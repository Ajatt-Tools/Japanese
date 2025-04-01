# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc

from ..database.sqlite3_buddy import Sqlite3Buddy
from .basic_types import FileUrlData


class AnkiAudioSourceManagerABC(abc.ABC):
    @abc.abstractmethod
    def search_audio(
        self,
        src_text: str,
        *,
        split_morphemes: bool,
        ignore_inflections: bool,
        stop_if_one_source_has_results: bool,
    ) -> list[FileUrlData]:
        raise NotImplementedError()

    @abc.abstractmethod
    def download_and_save_tags(self, hits, *, on_finish) -> None:
        raise NotImplementedError()


class AudioSourceManagerFactoryABC(abc.ABC):
    @abc.abstractmethod
    def request_new_session(self, db: Sqlite3Buddy) -> AnkiAudioSourceManagerABC:
        raise NotImplementedError()


class AudioSettingsConfigViewABC(abc.ABC):
    @property
    @abc.abstractmethod
    def dictionary_download_timeout(self) -> int:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def audio_download_timeout(self) -> int:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def attempts(self) -> int:
        raise NotImplementedError()
