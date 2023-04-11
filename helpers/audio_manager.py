# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import io
import json
import os
import pickle
import posixpath
import re
import zipfile
from types import SimpleNamespace
from typing import Optional, NewType, NamedTuple, Iterable, Union

import anki.httpclient
import requests
from requests import RequestException

try:
    from .file_ops import user_files_dir
    from ..mecab_controller.kana_conv import is_inflected
except ImportError:
    from file_ops import user_files_dir
    from mecab_controller.kana_conv import is_inflected


def file_exists(file_path: str):
    return (
            file_path
            and os.path.isfile(file_path)
            and os.stat(file_path).st_size > 0
    )


RE_FILENAME_PROHIBITED = re.compile(r'[\\\n\t\r#%&\[\]{}<>^*?/$!\'":@+`|=]+', flags=re.MULTILINE | re.IGNORECASE)
MAX_LEN_BYTES = 120 - 4


def cut_to_anki_size(text: str) -> str:
    return text.encode('utf-8')[:MAX_LEN_BYTES].decode('utf-8', errors='ignore')


def normalize_filename(text: str) -> str:
    """
    Since sources' names are used as filenames to store cache files on disk,
    ensure there are no questionable characters that some OSes may panic from.
    """
    import unicodedata
    text = cut_to_anki_size(text)
    text = unicodedata.normalize('NFC', text)
    text = re.sub(RE_FILENAME_PROHIBITED, '_', text)
    return text.strip()


FileInfo = NewType("FileInfo", dict[str, str])
FileList = NewType("FileList", list[str])


class FileUrlData(NamedTuple):
    url: str
    desired_filename: str
    reading: str = ""
    pitch_number: str = "?"


@dataclasses.dataclass
class AudioSourceConfig:
    enabled: bool
    name: str
    url: str

    @property
    def is_valid(self) -> str:
        return self.name and self.url

    @property
    def cache_path(self):
        return os.path.join(user_files_dir(), f"audio_source_{self.name}.pickle")


class AudioManagerHttpClient(anki.httpclient.HttpClient):
    # add some fake headers to convince sites we're not a bot.
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "TE": "trailers",
    }

    def __init__(
            self,
            addon_config: SimpleNamespace,
            progress_hook: Optional[anki.httpclient.ProgressCallback] = None
    ) -> None:
        super().__init__(progress_hook)
        self._audio_settings = addon_config.audio_settings

    def get(self, url: str, headers: dict[str, str] = None):
        # Mask the default get function in case it is called by mistake.
        raise NotImplementedError()

    def _get_with_timeout(self, url: str, timeout: int) -> requests.Response:
        # Set headers
        headers = self.headers.copy()
        headers["User-Agent"] = self._agent_name()

        # Set timeout
        timeout = timeout or self.timeout

        return self.session.get(
            url, stream=True, headers=headers, timeout=timeout, verify=self.verify
        )

    def _get_with_retry(self, url: str, timeout: int, attempts: int) -> requests.Response:
        for _attempt in range(min(max(0, attempts - 1), 99)):
            try:
                return self._get_with_timeout(url, timeout)
            except requests.Timeout:
                continue
        # If other tries timed out.
        return self._get_with_timeout(url, timeout)

    def download(self, file: Union[AudioSourceConfig, FileUrlData]) -> bytes:
        timeout = (
            self._audio_settings.dictionary_download_timeout
            if isinstance(file, AudioSourceConfig)
            else self._audio_settings.audio_download_timeout
        )
        attempts = self._audio_settings.attempts

        try:
            response = self._get_with_retry(file.url, timeout, attempts)
        except OSError as ex:
            raise AudioManagerException(
                file,
                f'{file.url} download failed with {ex.__class__.__name__}',
                exception=ex
            )
        if response.status_code != 200:
            raise AudioManagerException(
                file,
                f'{file.url} download failed with return code {response.status_code}',
                response=response
            )
        return self.stream_content(response)


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    pronunciation_data: Optional[dict] = dataclasses.field(init=False, default=None, repr=False)

    def resolve_file(self, word: str, file_name: str) -> FileUrlData:
        components = []
        file_info: FileInfo = self.files[file_name]

        for component in ('pitch_pattern', 'kana_reading'):
            if component in file_info:
                components.append(file_info[component])
                break

        if 'pitch_number' in file_info:
            components.append(file_info['pitch_number'])

        desired_filename = '_'.join((word, *components, self.name,))
        desired_filename = f'{normalize_filename(desired_filename)}{os.path.splitext(file_name)[-1]}'

        return FileUrlData(
            url=self.join(self.media_dir, file_name),
            desired_filename=desired_filename,
            reading=file_info.get('kana_reading', ''),
            pitch_number=file_info.get('pitch_number', '?')
        )

    def raise_if_not_ready(self):
        if not self.is_ready:
            raise RuntimeError("Attempt to access property of an uninitialized source.")

    @property
    def reported_name(self):
        self.raise_if_not_ready()
        return self.pronunciation_data['meta']['name']

    @property
    def media_dir(self) -> str:
        # Meta can specify absolute path to the media dir,
        # which will be used if set.
        # Otherwise, fall back to relative path.
        try:
            return self.pronunciation_data['meta']['media_dir_abs']
        except KeyError:
            return self.join(os.path.dirname(self.url), self.rel_media_dir)

    def join(self, *args):
        """ Join multiple paths. """
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return posixpath.join(*args)

    @property
    def rel_media_dir(self):
        self.raise_if_not_ready()
        return self.pronunciation_data['meta']['media_dir']

    @property
    def headwords(self) -> dict[str, FileList]:
        self.raise_if_not_ready()
        return self.pronunciation_data['headwords']

    @property
    def files(self) -> dict[str, FileInfo]:
        self.raise_if_not_ready()
        return self.pronunciation_data['files']

    @property
    def is_ready(self):
        return (
                self.pronunciation_data is not None
                and isinstance(self.pronunciation_data, dict)
                and 'meta' in self.pronunciation_data
        )

    @property
    def cache_exists(self):
        return file_exists(self.cache_path)

    @property
    def is_local(self) -> bool:
        return file_exists(self.url)

    @property
    def original_url(self):
        self.raise_if_not_ready()
        return self.pronunciation_data['meta']['original_url']

    @original_url.setter
    def original_url(self, url: str):
        self.raise_if_not_ready()
        self.pronunciation_data['meta']['original_url'] = url

    def pickle_self(self):
        # Remember where the file was downloaded from.
        self.original_url = self.url
        self.raise_if_not_ready()
        with open(self.cache_path, 'wb') as of:
            # Pickle the dictionary using the highest protocol available.
            pickle.dump(self.pronunciation_data, of, pickle.HIGHEST_PROTOCOL)

    def read_cache(self):
        with open(self.cache_path, 'rb') as f:
            print(f"Reading cached audio source: {self.cache_path}")
            self.pronunciation_data = pickle.load(f)

    def read_local_json(self):
        if self.url.endswith('.zip'):
            # Read from a zip file that is expected to contain a json file with audio source data.
            with zipfile.ZipFile(self.url) as zip_in:
                print(f"Reading local zip audio source: {self.url}")
                self.pronunciation_data = json.loads(read_zip(zip_in, self))
        else:
            # Read an uncompressed json file.
            with open(self.url, encoding='utf8') as f:
                print(f"Reading local json audio source: {self.url}")
                self.pronunciation_data = json.load(f)

    def download_remote_json(self, client: AudioManagerHttpClient):
        print(f"Downloading a remote audio source: {self.url}")
        bytes_data = client.download(self)

        try:
            self.pronunciation_data = json.loads(bytes_data)
        except UnicodeDecodeError:
            with zipfile.ZipFile(io.BytesIO(bytes_data)) as zip_in:
                self.pronunciation_data = json.loads(read_zip(zip_in, self))


@dataclasses.dataclass
class AudioManagerException(RequestException):
    file: Union[AudioSource, FileUrlData]
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None

    def describe_short(self) -> str:
        return str(
            self.exception.__class__.__name__
            if self.exception
            else
            self.response.status_code
        )


@dataclasses.dataclass
class InitResult:
    sources: list[AudioSource]
    errors: list[AudioManagerException]


def read_zip(zip_in: zipfile.ZipFile, file: AudioSource) -> bytes:
    try:
        return zip_in.read(next(
            name for name in zip_in.namelist()
            if name.endswith('.json')
        ))
    except (StopIteration, zipfile.BadZipFile) as ex:
        raise AudioManagerException(
            file,
            f"{ex.__class__.__name__}: json data isn't found in zip file {file.url}",
            exception=ex,
        )


class AudioSourceManager:
    def __init__(self, config: SimpleNamespace):
        self._config = config
        self._audio_sources: list[AudioSource] = []
        self._http_client = AudioManagerHttpClient(self._config)

    def get_file(self, file: FileUrlData) -> bytes:
        if os.path.isfile(file.url):
            with open(file.url, 'rb') as f:
                return f.read()
        else:
            return self._http_client.download(file)

    def _set_sources(self, sources: list[AudioSource]):
        self._audio_sources = sources

    def _init_dictionaries(self) -> InitResult:
        sources, errors = [], []
        for source in [AudioSource(**source) for source in self._config.audio_sources]:
            if not source.enabled:
                continue
            try:
                self._read_pronunciation_data(source)
            except AudioManagerException as ex:
                print(f"Ignoring audio source {source.name}: {ex.describe_short()}.")
                errors.append(ex)
                continue
            else:
                sources.append(source)
                print(f"Initialized audio source: {source.name}")
        return InitResult(sources, errors)

    def _read_pronunciation_data(self, source: AudioSource):
        if source.cache_exists:
            source.read_cache()
            # Check if the URLs mismatch,
            # e.g. when the user changed the URL without changing the name.
            if source.url == source.original_url:
                return
        if source.is_local:
            source.read_local_json()
        else:
            source.download_remote_json(self._http_client)
        source.pickle_self()

    def search_word(self, word: str) -> Iterable[FileUrlData]:
        for source in self._audio_sources:
            if word in source.headwords:
                for audio_file in source.headwords[word]:
                    file = source.resolve_file(word, audio_file)
                    if self._config.audio_settings.ignore_inflections and is_inflected(word, file.reading):
                        continue
                    yield file
                if self._config.audio_settings.stop_if_one_source_has_results:
                    break


# Entry point
##########################################################################


def main():
    # Used for testing when Anki isn't running.
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'config.json')) as inf:
        cfg = SimpleNamespace(**json.load(inf))
        cfg.audio_settings = SimpleNamespace(**cfg.audio_settings)  # type: ignore

    def init_audio_dictionaries(self: AudioSourceManager):
        self._set_sources(self._init_dictionaries().sources)

    aud_src_mgr = AudioSourceManager(cfg)
    init_audio_dictionaries(aud_src_mgr)
    for file in aud_src_mgr.search_word('原'):
        print(file)


if __name__ == '__main__':
    main()
