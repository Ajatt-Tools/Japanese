# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from aqt import mw

from japanese.audio_manager.audio_manager import AudioSourceManagerFactory
from japanese.audio_manager.basic_types import TotalAudioStats
from japanese.audio_manager.source_manager import AudioSourceManager
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from playground.utils import NoAnkiConfigView, persistent_sqlite3_db_path


class NoAnkiAudioSourceManagerFactory(AudioSourceManagerFactory):
    @property
    def db_path(self):
        return self._db_path

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


def init_testing_audio_manager(db_path: pathlib.Path) -> NoAnkiAudioSourceManagerFactory:
    # Used for testing when Anki isn't running.
    return NoAnkiAudioSourceManagerFactory(config=NoAnkiConfigView(), db_path=db_path)


def main() -> None:
    with persistent_sqlite3_db_path() as db_path:
        factory = init_testing_audio_manager(db_path)
        factory.init_sources()
        session: AudioSourceManager
        stats: TotalAudioStats
        with Sqlite3Buddy(db_path) as db:
            session = factory.request_new_session(db)
            stats = session.total_stats()
            print(f"{stats.unique_files=}")
            print(f"{stats.unique_headwords=}")
            for source_stats in stats.sources:
                print(source_stats)
            for file in session.search_word("ひらがな"):
                print(file)
            for source in session.audio_sources:
                print(f"source {source.name} media dir {source.media_dir}")


if __name__ == "__main__":
    main()
