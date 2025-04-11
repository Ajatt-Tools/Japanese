# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.database.audio_buddy import (
    AUDIO_TABLES_SCHEMA_NAME,
    AUDIO_TABLES_SCHEMA_VERSION,
)
from japanese.database.pitch_buddy import (
    PITCH_TABLES_SCHEMA_NAME,
    PITCH_TABLES_SCHEMA_VERSION,
)
from japanese.database.sqlite3_buddy import Sqlite3Buddy
from tests.conftest import tmp_db_connection


class TestDbVersion:
    def test_set_and_get(self, tmp_db_connection: Sqlite3Buddy) -> None:
        con = tmp_db_connection

        # at this point, the default tables should be prepared.
        assert con.get_db_version(AUDIO_TABLES_SCHEMA_NAME) == AUDIO_TABLES_SCHEMA_VERSION
        assert con.get_db_version(PITCH_TABLES_SCHEMA_NAME) == PITCH_TABLES_SCHEMA_VERSION

        # didn't insert this schema before
        assert con.get_db_version("test_schema_1") is None

        con.set_db_version("test_schema_1", 1)
        assert con.get_db_version("test_schema_1") == 1

        con.set_db_version("test_schema_2", 1)
        assert con.get_db_version("test_schema_2") == 1

        con.set_db_version("test_schema_1", 42)
        assert con.get_db_version("test_schema_1") == 42
