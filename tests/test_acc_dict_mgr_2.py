# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from typing import Callable

from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from japanese.pitch_accents.acc_dict_mgr_2 import AccDictToSqliteWriter
from tests.sqlite3_buddy import tmp_acc_db_writer, tmp_sqlite3_buddy


def test_table_ensure(tmp_sqlite3_buddy, tmp_acc_db_writer) -> None:
    with tmp_sqlite3_buddy as db:
        writer = tmp_acc_db_writer(db)
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False
        writer.ensure_sqlite_populated()
        assert writer.table_filled() is True
        assert writer.table_up_to_date() is True


def test_table_recreate(
    tmp_sqlite3_buddy: Sqlite3Buddy, tmp_acc_db_writer: Callable[[Sqlite3Buddy], AccDictToSqliteWriter]
) -> None:
    with tmp_sqlite3_buddy as db:
        writer = tmp_acc_db_writer(db)
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False
        writer.recreate_table()
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False
