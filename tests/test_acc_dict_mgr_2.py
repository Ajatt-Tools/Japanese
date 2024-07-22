# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from japanese.pitch_accents.acc_dict_mgr_2 import (
    SqliteAccDictReader,
    SqliteAccDictWriter,
)
from japanese.pitch_accents.common import FormattedEntry
from tests.sqlite3_buddy import tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file


class TestAccDictManager:
    @pytest.fixture(scope="class")
    def faux_writer(self, tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file):
        with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
            writer = SqliteAccDictWriter(db, tmp_upd_file, tmp_user_accents_file)
            yield writer

    @pytest.fixture(scope="class")
    def faux_reader(self, tmp_sqlite3_db_path):
        with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
            reader = SqliteAccDictReader(db)
            yield reader

    def test_empty(self, faux_writer) -> None:
        w = faux_writer
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False

    def test_table_recreate(self, faux_writer) -> None:
        w = faux_writer
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False
        w.recreate_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False

    def test_table_ensure(self, faux_writer) -> None:
        w = faux_writer
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False
        w.ensure_sqlite_populated()
        assert w.is_table_filled() is True
        assert w.is_table_up_to_date() is True

    def test_table_filled(self, faux_writer) -> None:
        w = faux_writer
        assert w.is_table_filled() is True
        assert w.is_table_up_to_date() is True

    def test_pitch_lookup(self, faux_reader) -> None:
        r = faux_reader
        result = r.look_up("僕")
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

    def test_table_clear(self, faux_writer) -> None:
        w = faux_writer
        assert w.is_table_filled() is True
        assert w.is_table_up_to_date() is True
        w.clear_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False
