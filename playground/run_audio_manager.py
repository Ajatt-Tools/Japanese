# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from japanese.audio_manager.audio_manager import AudioSourceManagerFactory
from japanese.audio_manager.source_manager import AudioSourceManager, TotalAudioStats
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from playground.utils import NoAnkiConfigView, persistent_sqlite3_db_path


class NoAnkiAudioSourceManagerFactory(AudioSourceManagerFactory):
    pass


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
