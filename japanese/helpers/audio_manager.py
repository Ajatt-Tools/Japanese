# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc
import contextlib
import dataclasses
import io
import json
import os
import posixpath
import re
import zipfile
from collections.abc import Iterable
from typing import Optional, Union

from ..config_view import JapaneseConfig
from ..mecab_controller.kana_conv import to_katakana
from ..pitch_accents.common import split_pitch_numbers
from .audio_json_schema import FileInfo
from .http_client import (
    AudioManagerException,
    AudioManagerHttpClient,
    AudioSourceConfig,
    FileUrlData,
)
from .sqlite3_buddy import BoundFile, Sqlite3Buddy, sqlite3_buddy


def file_exists(file_path: str):
    return file_path and os.path.isfile(file_path) and os.stat(file_path).st_size > 0


RE_FILENAME_PROHIBITED = re.compile(r'[\\\n\t\r#%&\[\]{}<>^*?/$!\'":@+`|=]+', flags=re.MULTILINE | re.IGNORECASE)
MAX_LEN_BYTES = 120 - 4


def cut_to_anki_size(text: str) -> str:
    return text.encode("utf-8")[:MAX_LEN_BYTES].decode("utf-8", errors="ignore")


def normalize_filename(text: str) -> str:
    """
    Since sources' names are used as filenames to store cache files on disk,
    ensure there are no questionable characters that some OSes may panic from.
    """
    import unicodedata

    text = cut_to_anki_size(text)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(RE_FILENAME_PROHIBITED, "_", text)
    return text.strip()


def norm_pitch_numbers(s: str) -> str:
    """
    Ensure that all pitch numbers of a word (pronunciation) are presented as a dash-separated string.
    When an audio file has more than one accent, it basically represents two or more words chained together.
    E.g., かも-知れない (1-0), 黒い-霧 (2-0), 作用,反作用の,法則 (1-3-0), 八幡,大菩薩 (2-3), 入り代わり-立ち代わり (0-0), 七転,八起き (3-1)
    """
    return "-".join(split_pitch_numbers(s)) or "?"


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    db: Optional[Sqlite3Buddy]

    def with_db(self, db: Optional[Sqlite3Buddy]):
        return dataclasses.replace(self, db=db)

    @classmethod
    def from_cfg(cls, source: AudioSourceConfig, db: Sqlite3Buddy) -> "AudioSource":
        return cls(**dataclasses.asdict(source), db=db)

    def to_cfg(self) -> AudioSourceConfig:
        """
        Used to compare changes in the config file.
        """
        data = dataclasses.asdict(self)
        del data["db"]
        return AudioSourceConfig(**data)

    def is_cached(self) -> bool:
        if not self.db:
            raise RuntimeError("db is none")
        return self.db.is_source_cached(self.name)

    def raise_if_not_ready(self):
        if not self.is_cached():
            raise RuntimeError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        # Meta can specify absolute path to the media dir,
        # which will be used if set.
        # Otherwise, fall back to relative path.
        self.raise_if_not_ready()
        assert self.db
        return self.db.get_media_dir_abs(self.name) or self.join(
            os.path.dirname(self.url), self.db.get_media_dir_rel(self.name)
        )

    def join(self, *args) -> Union[str, bytes]:
        """Join multiple paths."""
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return posixpath.join(*args)

    @property
    def is_local(self) -> bool:
        return file_exists(self.url)

    @property
    def original_url(self):
        self.raise_if_not_ready()
        assert self.db
        return self.db.get_original_url(self.name)

    def update_original_url(self):
        # Remember where the file was downloaded from.
        self.raise_if_not_ready()
        assert self.db
        self.db.set_original_url(self.name, self.url)

    def distinct_file_count(self) -> int:
        self.raise_if_not_ready()
        assert self.db
        return self.db.distinct_file_count(source_names=(self.name,))

    def distinct_headword_count(self) -> int:
        self.raise_if_not_ready()
        assert self.db
        return self.db.distinct_headword_count(source_names=(self.name,))


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
        return zip_in.read(next(name for name in zip_in.namelist() if name.endswith(".json")))
    except (StopIteration, zipfile.BadZipFile) as ex:
        raise AudioManagerException(
            audio_source,
            f"{ex.__class__.__name__}: json data isn't found in zip file {audio_source.url}",
            exception=ex,
        )


class AudioSourceManager:
    _config: JapaneseConfig
    _http_client: AudioManagerHttpClient
    _db: Sqlite3Buddy
    _audio_sources: dict[str, AudioSource]

    def __init__(
        self,
        config: JapaneseConfig,
        http_client: AudioManagerHttpClient,
        db: Sqlite3Buddy,
        audio_sources: list[AudioSource],
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._db = db
        self._audio_sources = {source.name: source.with_db(db) for source in audio_sources}

    @property
    def audio_sources(self) -> Iterable[AudioSource]:
        return self._audio_sources.values()

    def distinct_file_count(self) -> int:
        return self._db.distinct_file_count(source_names=tuple(source.name for source in self.audio_sources))

    def distinct_headword_count(self) -> int:
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

    def read_pronunciation_data(self, source: AudioSource) -> None:
        if source.is_cached():
            # Check if the URLs mismatch,
            # e.g. when the user changed the URL without changing the name.
            if source.url == source.original_url:
                return
            else:
                self._db.remove_data(source.name)
        if source.is_local:
            self._read_local_json(source)
        else:
            self._download_remote_json(source)
        source.update_original_url()

    def _resolve_file(self, source: AudioSource, file: BoundFile) -> FileUrlData:
        components: list[str] = []
        file_info: FileInfo = self._db.get_file_info(source.name, file.file_name)

        # Append either pitch pattern or kana reading, preferring pitch pattern.
        if file_info["pitch_pattern"]:
            components.append(to_katakana(file_info["pitch_pattern"]))
        elif file_info["kana_reading"]:
            components.append(to_katakana(file_info["kana_reading"]))

        # If pitch number is present, append it after reading.
        if file_info["pitch_number"]:
            components.append(norm_pitch_numbers(file_info["pitch_number"]))

        desired_filename = "_".join(
            (
                file.headword,
                *components,
                source.name,
            )
        )
        desired_filename = f"{normalize_filename(desired_filename)}{os.path.splitext(file.file_name)[-1]}"

        return FileUrlData(
            url=source.join(source.media_dir, file.file_name),
            desired_filename=desired_filename,
            word=file.headword,
            source_name=source.name,
            reading=(file_info["kana_reading"] or ""),
            pitch_number=(file_info["pitch_number"] or "?"),
        )

    def _read_local_json(self, source: AudioSource) -> None:
        if source.url.endswith(".zip"):
            # Read from a zip file that is expected to contain a json file with audio source data.
            with zipfile.ZipFile(source.url) as zip_in:
                print(f"Reading local zip audio source: {source.url}")
                self._db.insert_data(source.name, json.loads(read_zip(zip_in, source)))
        else:
            # Read an uncompressed json file.
            with open(source.url, encoding="utf8") as f:
                print(f"Reading local json audio source: {source.url}")
                self._db.insert_data(source.name, json.load(f))

    def _download_remote_json(self, source: AudioSource) -> None:
        print(f"Downloading a remote audio source: {source.url}")
        bytes_data = self._http_client.download(source)

        try:
            self._db.insert_data(source.name, json.loads(bytes_data))
        except UnicodeDecodeError:
            with zipfile.ZipFile(io.BytesIO(bytes_data)) as zip_in:
                self._db.insert_data(source.name, json.loads(read_zip(zip_in, source)))

    def _get_file(self, file: FileUrlData) -> bytes:
        if os.path.isfile(file.url):
            with open(file.url, "rb") as f:
                return f.read()
        else:
            return self._http_client.download(file)

    def remove_data(self, source_name: str) -> None:
        self._db.remove_data(source_name)


class AnkiAudioSourceManagerABC(abc.ABC):
    def search_audio(
        self,
        src_text: str,
        *,
        split_morphemes: bool,
        ignore_inflections: bool,
        stop_if_one_source_has_results: bool,
    ) -> list[FileUrlData]:
        raise NotImplementedError()

    def download_and_save_tags(self, hits, *, on_finish):
        raise NotImplementedError()


class AudioSourceManagerFactoryABC(abc.ABC):
    _config: JapaneseConfig
    _http_client: AudioManagerHttpClient
    _audio_sources: list[AudioSource]

    def __new__(cls, *args, **kwargs):
        try:
            obj = cls._instance  # type: ignore
        except AttributeError:
            obj = cls._instance = super().__new__(cls)
        return obj

    def __init__(self, config: JapaneseConfig) -> None:
        self._config = config
        self._http_client = AudioManagerHttpClient(self._config.audio_settings)
        self._audio_sources = []

    def purge_everything(self) -> None:
        self._audio_sources = []
        Sqlite3Buddy.remove_database_file()

    def request_new_session(self, db: Sqlite3Buddy) -> AudioSourceManager:
        raise NotImplementedError()

    def init_sources(self) -> None:
        self._set_sources(self._get_sources().sources)

    def _set_sources(self, sources: list[AudioSource]) -> None:
        self._audio_sources = [source.with_db(None) for source in sources]

    def _get_sources(self) -> InitResult:
        """
        This method is normally run in a different thread.
        A separate db connection is used.
        """
        sources, errors = [], []
        with sqlite3_buddy() as db:
            session = self.request_new_session(db)
            for source in [AudioSource.from_cfg(source, db) for source in self._config.iter_audio_sources()]:
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
