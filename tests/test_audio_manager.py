# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.audio_manager.audio_manager import AudioSourceManagerFactory
from japanese.audio_manager.source_manager import AudioSourceManager, TotalAudioStats
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from tests.no_anki_config import no_anki_config
from tests.sqlite3_buddy import tmp_sqlite3_db_path


class NoAnkiAudioSourceManagerFactory(AudioSourceManagerFactory):
    def request_new_session(self, db: Sqlite3Buddy) -> AudioSourceManager:
        return AudioSourceManager(
            config=self._config,
            http_client=self._http_client,
            db=db,
            audio_sources=self._audio_sources,
        )

    @property
    def db_path(self):
        return self._db_path


@pytest.fixture()
def init_factory(no_anki_config, tmp_sqlite3_db_path):
    factory = NoAnkiAudioSourceManagerFactory(config=no_anki_config, db_path=tmp_sqlite3_db_path)
    factory.init_sources()
    return factory


def test_audio_stats(init_factory) -> None:
    session: AudioSourceManager
    stats: TotalAudioStats

    with Sqlite3Buddy(init_factory.db_path) as db:
        session = init_factory.request_new_session(db)
        stats = session.total_stats()
        assert stats.unique_files == 19438
        assert stats.unique_headwords == 21569
        assert len(stats.sources) == 1
        assert stats.sources[0].num_files == 19438
        assert stats.sources[0].num_headwords == 21569
        assert len(list(session.search_word("ひらがな"))) == 3
