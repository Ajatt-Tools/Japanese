# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from typing import Callable

from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from japanese.pitch_accents.acc_dict_mgr_2 import (
    AccDictToSqliteReader,
    AccDictToSqliteWriter,
)
from japanese.pitch_accents.common import FormattedEntry
from tests.sqlite3_buddy import tmp_acc_db_writer, tmp_sqlite3_db_path


def test_table_recreate(
    tmp_sqlite3_db_path, tmp_acc_db_writer: Callable[[Sqlite3Buddy], AccDictToSqliteWriter]
) -> None:
    with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
        writer = tmp_acc_db_writer(db)
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False
        writer.recreate_table()
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False


def test_table_ensure(tmp_sqlite3_db_path, tmp_acc_db_writer) -> None:
    with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
        writer = tmp_acc_db_writer(db)
        assert writer.table_filled() is False
        assert writer.table_up_to_date() is False
        writer.ensure_sqlite_populated()
        assert writer.table_filled() is True
        assert writer.table_up_to_date() is True


def test_pitch_lookup(tmp_sqlite3_db_path):
    with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
        reader = AccDictToSqliteReader(db)
        result = reader.look_up_expr("僕")
        assert list(result) == [
            FormattedEntry(
                katakana_reading="ボク", html_notation="<low_rise>ボ</low_rise><high>ク</high>", pitch_number="0"
            ),
            FormattedEntry(
                katakana_reading="ボク", html_notation="<high_drop>ボ</high_drop><low>ク</low>", pitch_number="1"
            ),
            FormattedEntry(
                katakana_reading="シモベ", html_notation="<low_rise>シ</low_rise><high>モベ</high>", pitch_number="0"
            ),
            FormattedEntry(
                katakana_reading="シモベ",
                html_notation="<low_rise>シ</low_rise><high_drop>モベ</high_drop>",
                pitch_number="3",
            ),
            FormattedEntry(
                katakana_reading="ヤツガレ",
                html_notation="<low_rise>ヤ</low_rise><high>ツガレ</high>",
                pitch_number="0",
            ),
        ]
