# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import json
import os
import pickle
from types import SimpleNamespace
from typing import Optional, NewType, NamedTuple, Iterable

import anki.httpclient
import requests
from requests import RequestException

if __name__ == '__main__':
    from file_ops import user_files_dir
else:
    from .file_ops import user_files_dir


def file_exists(file_path: str):
    return (
            file_path
            and os.path.isfile(file_path)
            and os.stat(file_path).st_size > 0
    )


FileInfo = NewType("FileInfo", dict[str, str])
FileList = NewType("FileList", list[str])


class FileUrlData(NamedTuple):
    url: str
    desired_filename: str


@dataclasses.dataclass
class AudioSource:
    name: str
    url: str
    enabled: bool

    # current schema has three fields: "meta", "headwords", "files"
    pronunciation_data: Optional[dict] = dataclasses.field(init=False, default=None, repr=False)

    def resolve_file(self, word: str, file_name: str):
        components = []
        file_info: FileInfo = self.files[file_name]

        for component in ('pitch_pattern', 'kana_reading'):
            if component in file_info:
                components.append(file_info[component])
                break

        if 'pitch_number' in file_info:
            components.append(file_info['pitch_number'])

        return FileUrlData(
            url=os.path.join(os.path.dirname(self.url), self.rel_media_dir, file_name),
            desired_filename='_'.join((
                word,
                *components,
                self.name,
            )) + os.path.splitext(file_name)[-1],
        )

    @property
    def cache_path(self):
        return os.path.join(user_files_dir(), f"audio_source_{self.name}.pickle")

    def raise_if_not_ready(self):
        if not self.is_ready:
            raise RuntimeError("Attempt to access property of an uninitialized source.")

    @property
    def reported_name(self):
        self.raise_if_not_ready()
        return self.pronunciation_data['meta']['name']

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
        with open(self.url, encoding='utf8') as f:
            print(f"Reading local json audio source: {self.url}")
            self.pronunciation_data = json.load(f)

    def download_remote_json(self, client: anki.httpclient.HttpClient):
        self.pronunciation_data = json.loads(download(client, self))


@dataclasses.dataclass
class AudioManagerException(RequestException):
    file: AudioSource | FileUrlData
    explanation: str
    response: requests.Response | None = None
    exception: Exception | None = None

    def describe_short(self) -> str:
        return str(
            self.exception.__class__.__name__
            if self.exception
            else
            self.response.status_code
        )


def download(client: anki.httpclient.HttpClient, file: AudioSource | FileUrlData) -> bytes:
    try:
        response = client.get(file.url)
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
    return client.stream_content(response)


class AudioSourceManager:
    def __init__(self, config: SimpleNamespace):
        self._config = config
        self._audio_sources: list[AudioSource] = []
        self._http_client = anki.httpclient.HttpClient()
        self._http_client.timeout = self._config.download_timeout

    def get_file(self, file: FileUrlData):
        if os.path.isfile(file.url):
            with open(file.url, 'rb') as f:
                return f.read()
        else:
            return download(self._http_client, file)

    def set_sources(self, sources: list[AudioSource]):
        self._audio_sources = sources

    def init_dictionaries(self) -> list[AudioSource]:
        sources = []
        for source in [AudioSource(**source) for source in self._config.audio_sources]:
            if not source.enabled:
                continue
            try:
                self._read_pronunciation_data(source)
            except AudioManagerException as ex:
                print(f"Ignoring source {source.name}: {ex.describe_short()}.")
                continue
            else:
                sources.append(source)
        return sources

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
                    yield source.resolve_file(word, audio_file)


# Entry point
##########################################################################


def main():
    # Used for testing when Anki isn't running.
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'config.json')) as inf:
        cfg = SimpleNamespace(**json.load(inf))

    aud_src_mgr = AudioSourceManager(cfg)
    aud_src_mgr.set_sources(aud_src_mgr.init_dictionaries())
    for file in aud_src_mgr.search_word('原'):
        print(file)


if __name__ == '__main__':
    main()
