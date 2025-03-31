# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.audio_manager.audio_manager import AudioSourceManagerFactory
from japanese.audio_manager.basic_types import NameUrl, NameUrlSet, TotalAudioStats
from japanese.audio_manager.source_manager import AudioSourceManager
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from tests.conftest import tmp_sqlite3_db_path
from tests.no_anki_config import no_anki_config


class NoAnkiAudioSourceManagerFactory(AudioSourceManagerFactory):
    @property
    def db_path(self):
        return self._db_path


@pytest.fixture()
def init_factory(no_anki_config, tmp_sqlite3_db_path):
    factory = NoAnkiAudioSourceManagerFactory(config=no_anki_config, db_path=tmp_sqlite3_db_path)
    factory.init_sources()
    return factory


def test_audio_stats(init_factory: NoAnkiAudioSourceManagerFactory) -> None:
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


def test_delete_cache(init_factory: NoAnkiAudioSourceManagerFactory) -> None:
    with Sqlite3Buddy(init_factory.db_path) as db:
        session = init_factory.request_new_session(db)
        stats = session.total_stats()
        assert len(stats.sources) == 1
        test_source = db.get_source_by_name("TAAS-TEST-BAD")
        assert test_source is None
        test_source = db.get_source_by_name("TAAS-TEST")
        assert test_source.name == "TAAS-TEST"
        removed = session.remove_sources(NameUrlSet([test_source, NameUrl("TAAS-TEST-BAD", "")]))
        assert removed == [test_source]
        stats = session.total_stats()
        assert len(stats.sources) == 0
        assert stats.unique_files == 0
        assert stats.unique_headwords == 0
