# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import io
import json
import os
import re
import zipfile
from collections.abc import Iterable

from ..config_view import JapaneseConfig
from ..database.audio_buddy import BoundFile
from ..database.sqlite3_buddy import Sqlite3Buddy
from ..helpers.audio_json_schema import FileInfo
from ..helpers.basic_types import AudioManagerHttpClientABC
from ..mecab_controller.kana_conv import to_katakana
from ..pitch_accents.common import split_pitch_numbers
from ..pitch_accents.consts import NO_ACCENT
from .audio_source import AudioSource
from .basic_types import (
    AudioManagerException,
    FileUrlData,
    NameUrl,
    NameUrlSet,
    TotalAudioStats,
)

RE_FILENAME_PROHIBITED = re.compile(r'[\\\n\t\r#%&\[\]{}<>^*?/$!\'":@+`|=]+', flags=re.MULTILINE | re.IGNORECASE)
RE_UNDER = re.compile(r"_+", flags=re.MULTILINE | re.IGNORECASE)
MAX_LEN_BYTES = 120


def cut_to_anki_size(text: str, max_len_bytes: int) -> str:
    return text.encode("utf-8")[:max_len_bytes].decode("utf-8", errors="ignore")


def normalize_filename(text: str, suffix_size: int = 4) -> str:
    """
    Since audio files are stored on disk,
    ensure there are no questionable characters that some OSes may panic from.
    Suffix size is usually 4 bytes (.ogg, .mp3).
    """
    import unicodedata

    text = unicodedata.normalize("NFC", text)
    text = re.sub(RE_FILENAME_PROHIBITED, "_", text)
    text = re.sub(RE_UNDER, "_", text).strip("_")
    text = cut_to_anki_size(text, max_len_bytes=MAX_LEN_BYTES - suffix_size)
    return text.strip()


def norm_pitch_numbers(s: str) -> str:
    """
    Ensure that all pitch numbers of a word (pronunciation) are presented as a dash-separated string.
    When an audio file has more than one accent, it basically represents two or more words chained together.
    E.g., かも-知れない (1-0), 黒い-霧 (2-0), 作用,反作用の,法則 (1-3-0), 八幡,大菩薩 (2-3), 入り代わり-立ち代わり (0-0), 七転,八起き (3-1)
    """
    return "-".join(split_pitch_numbers(s)) or NO_ACCENT


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

    def __init__(
        self,
        config: JapaneseConfig,
        http_client: AudioManagerHttpClientABC,
        db: Sqlite3Buddy,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._db = db

    def iter_enabled_audio_sources(self) -> Iterable[AudioSource]:
        """
        Returns all enabled audio sources, regardless if they are initialized or not.
        """
        return (
            AudioSource.from_cfg(source, self._db) for source in self._config.iter_audio_sources() if source.enabled
        )

    def distinct_file_count(self) -> int:
        return self._db.distinct_file_count(
            source_names=tuple(source.name for source in self.iter_enabled_audio_sources())
        )

    def distinct_headword_count(self) -> int:
        return self._db.distinct_headword_count(
            source_names=tuple(source.name for source in self.iter_enabled_audio_sources())
        )

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
        for source in self.iter_enabled_audio_sources():
            for file in self._db.search_files_in_source(source.name, word):
                yield self._resolve_file(source, file)

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
        if file_info["pitch_number"] and file_info["pitch_number"] != NO_ACCENT:
            components.append(norm_pitch_numbers(file_info["pitch_number"]))

        desired_filename = "_".join((
            file.headword,
            *components,
            source.name,
        ))
        desired_filename = f"{normalize_filename(desired_filename)}{file.ext()}"
        return FileUrlData(
            url=source.join_media_path(source.media_dir, file.file_name),
            desired_filename=desired_filename,
            word=file.headword,
            source_name=source.name,
            reading=(file_info["kana_reading"] or ""),
            pitch_number=(file_info["pitch_number"] or NO_ACCENT),
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

    def already_initialized(self) -> frozenset[NameUrl]:
        """
        Returns audio sources that are cached in the database.
        """
        return frozenset(self._db.get_cached_sources())

    def must_be_initialized(self) -> frozenset[NameUrl]:
        """
        Returns audio sources that the add-on needs right now based on the current config.
        """
        return frozenset(NameUrl(s.name, s.url) for s in self._config.iter_audio_sources() if s.enabled)

    def requires_init_operation(self) -> frozenset[NameUrl]:
        """
        Returns a set of audio sources that are enabled but not initialized.
        Used to skip unnecessary re-init operations.
        Count only enabled sources. Disabled sources have no effect on the audio manager's operation.
        """
        return self.must_be_initialized() - self.already_initialized()

    def get_sources(self) -> InitResult:
        """
        This method is normally run in a different thread.
        A separate db connection is used.
        """
        sources, errors = [], []
        for source in self.iter_enabled_audio_sources():
            try:
                self.read_pronunciation_data(source)
            except AudioManagerException as ex:
                print(f"Ignoring audio source {source.name}: {ex.describe_short()}.")
                errors.append(ex)
                continue
            except Exception as ex:
                print(ex)
                errors.append(AudioManagerException(source, str(ex), exception=ex))
            else:
                sources.append(source)
                print(f"Initialized audio source: {source.name}")
        return InitResult(sources, errors)
