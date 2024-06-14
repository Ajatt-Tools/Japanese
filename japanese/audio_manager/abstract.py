# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc

from ..helpers.http_client import FileUrlData
from ..helpers.sqlite3_buddy import Sqlite3Buddy
from .source_manager import AudioSourceManager


class AudioSourceManagerFactoryABC(abc.ABC):
    @abc.abstractmethod
    def request_new_session(self, db: Sqlite3Buddy) -> AudioSourceManager:
        raise NotImplementedError()


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
    def download_and_save_tags(self, hits, *, on_finish):
        raise NotImplementedError()
