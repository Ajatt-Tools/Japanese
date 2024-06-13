# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.helpers.audio_manager import (
    AudioSourceManager,
    AudioSourceManagerFactoryABC,
    TotalAudioStats,
)
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy, sqlite3_buddy
from tests.no_anki_config import NoAnkiConfigView


class NoAnkiAudioSourceManagerFactory(AudioSourceManagerFactoryABC):
    def request_new_session(self, db: Sqlite3Buddy) -> AudioSourceManager:
        """
        If tasks are being done in a different thread, prepare a new db connection
        to avoid sqlite3 throwing an instance of sqlite3.ProgrammingError.
        """
        return AudioSourceManager(
            config=self._config,
            http_client=self._http_client,
            db=db,
            audio_sources=self._audio_sources,
        )


def init_testing_audio_manager() -> NoAnkiAudioSourceManagerFactory:
    # Used for testing when Anki isn't running.
    return NoAnkiAudioSourceManagerFactory(config=NoAnkiConfigView())


def main() -> None:
    factory = init_testing_audio_manager()
    factory.init_sources()
    session: AudioSourceManager
    stats: TotalAudioStats

    with sqlite3_buddy() as db:
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
