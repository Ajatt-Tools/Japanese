# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
from collections.abc import Iterable
from typing import Optional

from aqt import mw

from ..config_view import JapaneseConfig
from ..helpers.basic_types import AudioManagerHttpClientABC
from ..helpers.http_client import AudioManagerHttpClient
from ..helpers.sqlite3_buddy import InvalidSourceIndex, Sqlite3Buddy
from .audio_source import AudioSource
from .basic_types import AudioManagerException, AudioSourceConfig, NameUrl, NameUrlSet
from .source_manager import AudioSourceManager, InitResult


class AudioSourceManagerFactory:
    _config: JapaneseConfig
    _http_client: AudioManagerHttpClientABC
    _audio_sources: list[AudioSource]
    _db_path: Optional[pathlib.Path] = None

    def __new__(cls, *args, **kwargs):
        try:
            obj = cls._instance  # type: ignore
        except AttributeError:
            obj = cls._instance = super().__new__(cls)
        return obj

    def __init__(self, config: JapaneseConfig, db_path: Optional[pathlib.Path] = None) -> None:
        self._config = config
        self._db_path = db_path or self._db_path
        self._http_client = AudioManagerHttpClient(self._config.audio_settings)
        self._audio_sources = []
        if mw:
            assert self._db_path is None

    @property
    def http_client(self) -> AudioManagerHttpClientABC:
        return self._http_client

    @property
    def audio_sources(self) -> list[AudioSource]:
        return self._audio_sources

    def request_new_session(self, db: Sqlite3Buddy) -> AudioSourceManager:
        """
        If tasks are being done in a different thread, prepare a new db connection
        to avoid sqlite3 throwing an instance of sqlite3.ProgrammingError.
        """
        assert mw is None, "Anki shouldn't be running"
        return AudioSourceManager(
            config=self._config,
            http_client=self._http_client,
            db=db,
            audio_sources=self._audio_sources,
        )

    def init_sources(self) -> None:
        assert mw is None, "Anki shouldn't be running"
        with Sqlite3Buddy(self._db_path) as db:
            session = self.request_new_session(db)
            result = self.get_sources(session)
            print(f"{result.did_run=}")
            print(f"{result.errors=}")
            print(f"{result.sources=}")
            self.set_sources(result.sources)

    def set_sources(self, sources: list[AudioSource]) -> None:
        self._audio_sources = [source.with_db(None) for source in sources]

    def _iter_audio_sources(self, db: Sqlite3Buddy) -> Iterable[AudioSource]:
        return (AudioSource.from_cfg(source, db) for source in self._config.iter_audio_sources())

    def get_sources(self, session: AudioSourceManager) -> InitResult:
        """
        This method is normally run in a different thread.
        A separate db connection is used.
        """
        sources, errors = [], []
        for source in self._iter_audio_sources(session.buddy):
            if not source.enabled:
                continue
            try:
                session.read_pronunciation_data(source)
            except AudioManagerException as ex:
                print(f"Ignoring audio source {source.name}: {ex.describe_short()}.")
                errors.append(ex)
                continue
            except InvalidSourceIndex as ex:
                print(ex)
                errors.append(AudioManagerException(source, str(ex)))
            else:
                sources.append(source)
                print(f"Initialized audio source: {source.name}")
        return InitResult(sources, errors)

    def purge_sources(self) -> None:
        """
        This method is normally run in a different thread.
        A separate db connection is used.
        """
        with Sqlite3Buddy(self._db_path) as db:
            session = self.request_new_session(db)
            session.clear_audio_tables()

    def remove_selected(self, sources_to_delete: NameUrlSet) -> list[AudioSourceConfig]:
        """
        Remove selected sources from the database.
        Config file stays unchanged.
        """
        removed: list[AudioSourceConfig] = []
        with Sqlite3Buddy(self._db_path) as db:
            session = self.request_new_session(db)
            for cached in session.audio_sources:
                if NameUrl(cached.name, cached.url) in sources_to_delete:
                    session.remove_data(cached.name)
                    removed.append(cached)
                    print(f"Removed cache for source: {cached.name} ({cached.url})")
                else:
                    print(f"Source isn't cached: {cached.name} ({cached.url})")
        return removed
