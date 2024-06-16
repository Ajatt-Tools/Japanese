# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc

from ..config_view import JapaneseConfig
from ..helpers.basic_types import AudioManagerHttpClientABC
from ..helpers.http_client import AudioManagerHttpClient
from ..helpers.sqlite3_buddy import Sqlite3Buddy, sqlite3_buddy
from .abstract import AudioSourceManagerFactoryABC
from .audio_source import AudioSource
from .basic_types import AudioManagerException
from .source_manager import InitResult


class AudioSourceManagerFactory(AudioSourceManagerFactoryABC, abc.ABC):
    _config: JapaneseConfig
    _http_client: AudioManagerHttpClientABC
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
