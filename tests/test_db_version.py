# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.database.basic_types import Sqlite3BuddyGetVersionError
from japanese.database.sqlite3_buddy import Sqlite3Buddy
from tests.conftest import tmp_db_connection


class TestDbVersion:
    def test_set_and_get(self, tmp_db_connection: Sqlite3Buddy) -> None:
        con = tmp_db_connection
        # verify that everything is empty
        cur = con.con.execute("""
        SELECT COUNT(*) FROM version
        """)
        assert cur.fetchone()[0] == 0, "table should not be filled yet"
        with pytest.raises(Sqlite3BuddyGetVersionError):
            # version is not set yet => get exception
            con.get_db_version("test_schema_1")
        con.set_db_version("test_schema_1", 1)
        assert con.get_db_version("test_schema_1") == 1
        con.set_db_version("test_schema_2", 1)
        assert con.get_db_version("test_schema_2") == 1
        con.set_db_version("test_schema_1", 42)
        assert con.get_db_version("test_schema_1") == 42
