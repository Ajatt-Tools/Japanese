# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import contextlib
import dataclasses
import io
import json
import os
import re
import zipfile
from collections.abc import Iterable
from typing import Sequence

from ..config_view import JapaneseConfig
from ..helpers.audio_json_schema import FileInfo
from ..helpers.basic_types import AudioManagerHttpClientABC
from ..helpers.sqlite3_buddy import BoundFile, Sqlite3Buddy
from ..mecab_controller.kana_conv import to_katakana
from ..pitch_accents.common import split_pitch_numbers
from .audio_source import AudioSource
from .basic_types import (
    AudioManagerException,
    AudioSourceConfig,
    FileUrlData,
    NameUrl,
    NameUrlSet,
    TotalAudioStats,
)

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
class InitResult:
    sources: list[AudioSource]
    errors: list[AudioManagerException]
    did_run: bool = True

    @classmethod
    def did_not_run(cls):
        # indicates that the init operation didn't start (it wasn't necessary)
        return cls([], [], did_run=False)


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
    _http_client: AudioManagerHttpClientABC
    _db: Sqlite3Buddy
    _audio_sources: dict[str, AudioSource]

    def __init__(
        self,
        config: JapaneseConfig,
        http_client: AudioManagerHttpClientABC,
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

    @property
    def buddy(self) -> Sqlite3Buddy:
        return self._db

    def distinct_file_count(self) -> int:
        return self._db.distinct_file_count(source_names=tuple(source.name for source in self.audio_sources))

    def distinct_headword_count(self) -> int:
        return self._db.distinct_headword_count(source_names=tuple(source.name for source in self.audio_sources))

    def total_stats(self) -> TotalAudioStats:
        return TotalAudioStats(
            unique_files=self.distinct_file_count(),
            unique_headwords=self.distinct_headword_count(),
            sources=[
                stats
                for source in self._config.iter_audio_sources()
                if (stats := self._db.get_stats_by_name(NameUrl(source.name, source.url)))
            ],
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
            with io.BytesIO(bytes_data) as file, zipfile.ZipFile(file) as zip_in:
                self._db.insert_data(source.name, json.loads(read_zip(zip_in, source)))

    def _get_file(self, file: FileUrlData) -> bytes:
        if os.path.isfile(file.url):
            with open(file.url, "rb") as f:
                return f.read()
        else:
            return self._http_client.download(file)

    def remove_data(self, source_name: str) -> None:
        self._db.remove_data(source_name)

    def remove_sources(self, sources_to_delete: NameUrlSet) -> list[NameUrl]:
        """
        Remove audio sources from the database.
        Config file stays unchanged.
        """
        removed: list[NameUrl] = []
        for to_delete in sources_to_delete:
            cached = self._db.get_source_by_name(to_delete.name)
            if cached and cached == to_delete:
                self.remove_data(to_delete.name)
                removed.append(to_delete)
                print(f"Removed cache for source: {to_delete.name} ({to_delete.url})")
            else:
                print(f"Source isn't cached: {to_delete.name} ({to_delete.url})")
        return removed

    def clear_audio_tables(self) -> None:
        self._db.clear_all_audio_data()

    def already_initialized(self) -> Sequence[AudioSourceConfig]:
        """
        Returns audio sources that have been fully initialized,
        meaning they are enabled and the database has cached them.
        """
        return tuple(s.to_cfg() for s in self._audio_sources.values() if s.enabled and s.is_cached())

    def must_be_initialized(self) -> Sequence[AudioSourceConfig]:
        """
        Returns audio sources that the add-on needs right now based on the current config.
        """
        return tuple(s for s in self._config.iter_audio_sources() if s.enabled)

    def source_config_changed(self) -> bool:
        """
        Returns true if the configuration of audio sources has changed.
        Used to skip unnecessary re-init operations.
        Count only enabled sources. Disabled sources have no effect on the audio manager's operation.
        """
        return self.already_initialized() != self.must_be_initialized()
