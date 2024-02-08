# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import contextlib
import dataclasses
import io
import json
import os
import posixpath
import re
import zipfile
from collections.abc import Iterable
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Optional, Union, cast

import anki.httpclient
import requests
from requests import RequestException

try:
    from ..pitch_accents.common import split_pitch_numbers
    from .audio_json_schema import FileInfo
    from .sqlite3_buddy import Sqlite3Buddy, BoundFile
    from .file_ops import user_files_dir
    from ..mecab_controller.kana_conv import to_katakana
    from .inflections import is_inflected
except ImportError:
    from pitch_accents.common import split_pitch_numbers
    from helpers.audio_json_schema import FileInfo
    from helpers.sqlite3_buddy import Sqlite3Buddy, BoundFile
    from helpers.file_ops import user_files_dir
    from helpers.inflections import is_inflected
    from mecab_controller.kana_conv import to_katakana


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


@dataclasses.dataclass(frozen=True)
class FileUrlData:
    url: str
    desired_filename: str
    word: str
    source_name: str
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
        """
        Get an audio source or audio file.
        """
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
        if response.status_code != requests.codes.ok:
            raise AudioManagerException(
                file,
                f'{file.url} download failed with return code {response.status_code}',
                response=response
            )
        return self.stream_content(response)


def norm_pitch_numbers(s: str) -> str:
    """
    Ensure that all pitch numbers of a word (pronunciation) are presented as a dash-separated string.
    When an audio file has more than one accent, it basically represents two or more words chained together.
    E.g., かも-知れない (1-0), 黒い-霧 (2-0), 作用,反作用の,法則 (1-3-0), 八幡,大菩薩 (2-3), 入り代わり-立ち代わり (0-0), 七転,八起き (3-1)
    """
    return '-'.join(split_pitch_numbers(s)) or '?'


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    db: Optional[Sqlite3Buddy]

    def raise_if_not_ready(self):
        if not self.is_cached:
            raise RuntimeError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        # Meta can specify absolute path to the media dir,
        # which will be used if set.
        # Otherwise, fall back to relative path.
        self.raise_if_not_ready()
        return (
                self.db.get_media_dir_abs(self.name)
                or self.join(os.path.dirname(self.url), self.db.get_media_dir_rel(self.name))
        )

    def join(self, *args) -> str:
        """ Join multiple paths. """
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return posixpath.join(*args)

    @property
    def is_cached(self) -> bool:
        return self.db.is_source_cached(self.name)

    @property
    def is_local(self) -> bool:
        return file_exists(self.url)

    @property
    def original_url(self):
        self.raise_if_not_ready()
        return self.db.get_original_url(self.name)

    def update_original_url(self):
        # Remember where the file was downloaded from.
        self.raise_if_not_ready()
        self.db.set_original_url(self.name, self.url)

    def distinct_file_count(self) -> int:
        return self.db.distinct_file_count(source_names=(self.name,))

    def distinct_headword_count(self) -> int:
        return self.db.distinct_headword_count(source_names=(self.name,))


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


@dataclasses.dataclass(frozen=True)
class AudioStats:
    source_name: str
    num_files: int
    num_headwords: int


@dataclasses.dataclass(frozen=True)
class TotalAudioStats:
    unique_headwords: int
    unique_files: int
    sources: list[AudioStats]


def read_zip(zip_in: zipfile.ZipFile, audio_source: AudioSource) -> bytes:
    try:
        return zip_in.read(next(
            name for name in zip_in.namelist()
            if name.endswith('.json')
        ))
    except (StopIteration, zipfile.BadZipFile) as ex:
        raise AudioManagerException(
            audio_source,
            f"{ex.__class__.__name__}: json data isn't found in zip file {audio_source.url}",
            exception=ex,
        )


class AudioSourceManager:
    def __init__(
            self, config: SimpleNamespace,
            http_client: Optional[AudioManagerHttpClient],
            db: Sqlite3Buddy,
            audio_sources: list[AudioSource],
    ):
        self._config = config
        self._http_client = http_client
        self._db: Sqlite3Buddy = db
        self._audio_sources: dict[str, AudioSource] = {
            source.name: dataclasses.replace(source, db=self._db)
            for source in audio_sources
        }

    @property
    def audio_sources(self) -> Iterable[AudioSource]:
        return self._audio_sources.values()

    @property
    def db(self) -> Sqlite3Buddy:
        return self._db

    def distinct_file_count(self):
        return self._db.distinct_file_count(source_names=tuple(source.name for source in self.audio_sources))

    def distinct_headword_count(self):
        return self._db.distinct_headword_count(source_names=tuple(source.name for source in self.audio_sources))

    def total_stats(self) -> TotalAudioStats:
        stats = [
            AudioStats(
                source_name=source.name,
                num_files=source.distinct_file_count(),
                num_headwords=source.distinct_headword_count(),
            )
            for source in self.audio_sources
        ]
        return TotalAudioStats(
            unique_files=self.distinct_file_count(),
            unique_headwords=self.distinct_headword_count(),
            sources=stats,
        )

    def search_word(self, word: str) -> Iterable[FileUrlData]:
        for source_name in self._audio_sources:
            for file in self._db.search_files_in_source(source_name, word):
                with contextlib.suppress(KeyError):
                    # Accessing a disabled source results in a key error.
                    yield self._resolve_file(self._audio_sources[file.source_name], file)

    def read_pronunciation_data(self, source: AudioSource):
        if source.is_cached:
            # Check if the URLs mismatch,
            # e.g. when the user changed the URL without changing the name.
            if source.url == source.original_url:
                return
            else:
                self.db.remove_data(source.name)
        if source.is_local:
            self._read_local_json(source)
        else:
            self._download_remote_json(source)
        source.update_original_url()

    def _resolve_file(self, source: AudioSource, file: BoundFile) -> FileUrlData:
        components: list[str] = []
        file_info: FileInfo = self._db.get_file_info(source.name, file.file_name)

        # Append either pitch pattern or kana reading, preferring pitch pattern.
        if file_info['pitch_pattern']:
            components.append(to_katakana(file_info['pitch_pattern']))
        elif file_info['kana_reading']:
            components.append(to_katakana(file_info['kana_reading']))

        # If pitch number is present, append it after reading.
        if file_info['pitch_number']:
            components.append(norm_pitch_numbers(file_info['pitch_number']))

        desired_filename = '_'.join((file.headword, *components, source.name,))
        desired_filename = f'{normalize_filename(desired_filename)}{os.path.splitext(file.file_name)[-1]}'

        return FileUrlData(
            url=source.join(source.media_dir, file.file_name),
            desired_filename=desired_filename,
            word=file.headword,
            source_name=source.name,
            reading=(file_info['kana_reading'] or ""),
            pitch_number=(file_info['pitch_number'] or "?"),
        )

    def _read_local_json(self, source: AudioSource):
        if source.url.endswith('.zip'):
            # Read from a zip file that is expected to contain a json file with audio source data.
            with zipfile.ZipFile(source.url) as zip_in:
                print(f"Reading local zip audio source: {source.url}")
                self.db.insert_data(source.name, json.loads(read_zip(zip_in, source)))
        else:
            # Read an uncompressed json file.
            with open(source.url, encoding='utf8') as f:
                print(f"Reading local json audio source: {source.url}")
                self.db.insert_data(source.name, json.load(f))

    def _download_remote_json(self, source: AudioSource):
        print(f"Downloading a remote audio source: {source.url}")
        bytes_data = self._http_client.download(source)

        try:
            self.db.insert_data(source.name, json.loads(bytes_data))
        except UnicodeDecodeError:
            with zipfile.ZipFile(io.BytesIO(bytes_data)) as zip_in:
                self.db.insert_data(source.name, json.loads(read_zip(zip_in, source)))

    def _get_file(self, file: FileUrlData) -> bytes:
        if os.path.isfile(file.url):
            with open(file.url, 'rb') as f:
                return f.read()
        else:
            return self._http_client.download(file)


class AudioSourceManagerFactory:
    def __new__(cls, *args, **kwargs):
        try:
            obj = cls._instance  # type: ignore
        except AttributeError:
            obj = cls._instance = super().__new__(cls)
        return obj

    def __init__(self, config: SimpleNamespace, mgr_class: type):
        self._mgr_class = mgr_class
        self._config = config
        self._http_client = AudioManagerHttpClient(self._config)
        self._audio_sources: list[AudioSource] = []

    def purge_everything(self):
        self._audio_sources = []
        Sqlite3Buddy.remove_database_file()

    @contextmanager
    def request_new_session(self):
        """
        If tasks are being done in a different thread, prepare a new db connection
        to avoid sqlite3 throwing an instance of sqlite3.ProgrammingError.
        """
        with Sqlite3Buddy.new_session() as db:
            yield self._mgr_class(
                config=self._config,
                http_client=self._http_client,
                db=db,
                audio_sources=self._audio_sources,
            )

    def init_sources(self):
        self._set_sources(self._get_sources().sources)

    def _set_sources(self, sources: list[AudioSource]):
        self._audio_sources = [dataclasses.replace(source, db=None) for source in sources]

    def _get_sources(self) -> InitResult:
        """
        This method is normally run in a different thread.
        A separate db connection is used.
        """
        sources, errors = [], []
        with self.request_new_session() as session:
            for source in [AudioSource(**source, db=session.db) for source in self._config.audio_sources]:
                if not source.enabled:
                    continue
                try:
                    session.read_pronunciation_data(source)
                except AudioManagerException as ex:
                    print(f"Ignoring audio source {source.name}: {ex.describe_short()}.")
                    errors.append(ex)
                    continue
                else:
                    sources.append(source)
                    print(f"Initialized audio source: {source.name}")
            return InitResult(sources, errors)


# Debug
##########################################################################


def init_testing_audio_manager():
    # Used for testing when Anki isn't running.
    with open(os.path.join(os.path.dirname(__file__), os.pardir, 'config.json')) as inf:
        cfg = SimpleNamespace(**json.load(inf))
        cfg.audio_settings = SimpleNamespace(**cast(dict, cfg.audio_settings))
    return AudioSourceManagerFactory(cfg, AudioSourceManager)


def main():
    factory = init_testing_audio_manager()
    factory.init_sources()

    with factory.request_new_session() as aud_mgr:
        aud_mgr: AudioSourceManager
        stats: TotalAudioStats = aud_mgr.total_stats()
        print(f"{stats.unique_files=}")
        print(f"{stats.unique_headwords=}")
        for source_stats in stats.sources:
            print(source_stats)
        for file in aud_mgr.search_word('ひらがな'):
            print(file)
        for source in aud_mgr.audio_sources:
            print(f"source {source.name} media dir {source.media_dir}")


if __name__ == '__main__':
    main()
