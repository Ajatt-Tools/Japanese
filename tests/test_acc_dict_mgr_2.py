# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

import pytest

from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.pitch_accents.acc_dict_mgr_2 import (
    SqliteAccDictReader,
    SqliteAccDictWriter,
    iter_bundled_pitch_accent_files,
)
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.consts import FORMATTED_ACCENTS_TSV
from tests.conftest import tmp_db_connection, tmp_upd_file, tmp_user_accents_file


def test_iter_bundled_pitch_accent_files() -> None:
    names = [path.name for path in iter_bundled_pitch_accent_files(FORMATTED_ACCENTS_TSV)]
    assert names == ["pitch_accents_formatted.1.csv", "pitch_accents_formatted.2.csv", "pitch_accents_formatted.3.csv"]


class TestAccDictEmpty:
    """Tests that verify behavior on a fresh, unpopulated table."""

    @pytest.fixture(scope="class")
    def faux_writer(
        self, tmp_db_connection: Sqlite3Buddy, tmp_upd_file: pathlib.Path, tmp_user_accents_file: pathlib.Path
    ) -> SqliteAccDictWriter:
        writer = SqliteAccDictWriter(tmp_db_connection, tmp_upd_file, tmp_user_accents_file)
        yield writer

    def test_empty(self, faux_writer: SqliteAccDictWriter) -> None:
        w = faux_writer
        w.clear_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False

    def test_table_recreate(self, faux_writer: SqliteAccDictWriter) -> None:
        w = faux_writer
        w.clear_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False
        w.recreate_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False

    def test_table_ensure(self, faux_writer: SqliteAccDictWriter) -> None:
        w = faux_writer
        w.clear_table()
        assert w.is_table_filled() is False
        assert w.is_table_up_to_date() is False
        w.ensure_sqlite_populated()
        assert w.is_table_filled() is True
        assert w.is_table_up_to_date() is True


class TestAccDictPopulated:
    """Tests that verify behavior on a pre-populated table."""

    @pytest.fixture(scope="class")
    def faux_writer(
        self, tmp_db_connection: Sqlite3Buddy, tmp_upd_file: pathlib.Path, tmp_user_accents_file: pathlib.Path
    ) -> SqliteAccDictWriter:
        writer = SqliteAccDictWriter(tmp_db_connection, tmp_upd_file, tmp_user_accents_file)
        writer.ensure_sqlite_populated()
        yield writer

    @pytest.fixture(scope="class")
    def faux_reader(self, tmp_db_connection: Sqlite3Buddy, faux_writer: SqliteAccDictWriter) -> SqliteAccDictReader:
        reader = SqliteAccDictReader(tmp_db_connection)
        yield reader

    def test_table_filled(self, faux_writer: SqliteAccDictWriter) -> None:
        w = faux_writer
        assert w.is_table_filled() is True
        assert w.is_table_up_to_date() is True

    def test_pitch_lookup(self, faux_reader: SqliteAccDictReader) -> None:
        r = faux_reader
        result = r.look_up("僕")
        assert list(result) == [
            FormattedEntry(
                raw_headword="僕",
                katakana_reading="ボク",
                html_notation="<low_rise>ボ</low_rise><high>ク</high>",
                pitch_number="0",
            ),
            FormattedEntry(
                raw_headword="僕",
                katakana_reading="ボク",
                html_notation="<high_drop>ボ</high_drop><low>ク</low>",
                pitch_number="1",
            ),
            FormattedEntry(
                raw_headword="僕",
                katakana_reading="シモベ",
                html_notation="<low_rise>シ</low_rise><high>モベ</high>",
                pitch_number="0",
            ),
            FormattedEntry(
                raw_headword="僕",
                katakana_reading="シモベ",
                html_notation="<low_rise>シ</low_rise><high_drop>モベ</high_drop>",
                pitch_number="3",
            ),
            FormattedEntry(
                raw_headword="僕",
                katakana_reading="ヤツガレ",
                html_notation="<low_rise>ヤ</low_rise><high>ツガレ</high>",
                pitch_number="0",
            ),
        ]

    def test_pitch_lookup_as_dict(self, faux_reader: SqliteAccDictReader) -> None:
        r = faux_reader
        result = r.look_up_grouped("あくび")
        assert result == {
            "欠伸": [
                FormattedEntry(
                    raw_headword="欠伸",
                    katakana_reading="アクビ",
                    html_notation="<low_rise>ア</low_rise><high>クビ</high>",
                    pitch_number="0",
                )
            ],
            "悪日": [
                FormattedEntry(
                    raw_headword="悪日",
                    katakana_reading="アクビ",
                    html_notation="<high_drop>ア</high_drop><low>クビ</low>",
                    pitch_number="1",
                ),
                FormattedEntry(
                    raw_headword="悪日",
                    katakana_reading="アクビ",
                    html_notation="<low_rise>ア</low_rise><high_drop>ク</high_drop><low>ビ</low>",
                    pitch_number="2",
                ),
            ],
            "アクビ": [
                FormattedEntry(
                    raw_headword="欠伸",
                    katakana_reading="アクビ",
                    html_notation="<low_rise>ア</low_rise><high>クビ</high>",
                    pitch_number="0",
                ),
                FormattedEntry(
                    raw_headword="悪日",
                    katakana_reading="アクビ",
                    html_notation="<high_drop>ア</high_drop><low>クビ</low>",
                    pitch_number="1",
                ),
                FormattedEntry(
                    raw_headword="悪日",
                    katakana_reading="アクビ",
                    html_notation="<low_rise>ア</low_rise><high_drop>ク</high_drop><low>ビ</low>",
                    pitch_number="2",
                ),
            ],
            "欠": [
                FormattedEntry(
                    raw_headword="欠",
                    katakana_reading="アクビ",
                    html_notation="<low_rise>ア</low_rise><high>クビ</high>",
                    pitch_number="0",
                )
            ],
        }

    def test_pitch_lookup_overridden_by_user(self, faux_reader: SqliteAccDictReader) -> None:
        """
        There's some fake pitch data in the test user's file.
        It should properly override the bundled data.
        """
        r = faux_reader
        result = r.look_up("言葉")
        assert list(result) == [
            FormattedEntry(
                raw_headword="言葉",
                katakana_reading="ソウシツ",
                html_notation="<low_rise>ソ</low_rise><high>ウシツ</high>",
                pitch_number="0",
            ),
            FormattedEntry(
                raw_headword="言葉",
                katakana_reading="ソゴ",
                html_notation="<low_rise>ソ</low_rise><high>ゴ</high>",
                pitch_number="0",
            ),
        ]
        result = r.look_up("×××")
        assert list(result) == [
            FormattedEntry(
                raw_headword="×××",
                katakana_reading="デタラメ",
                html_notation="<low_rise>デ</low_rise><high>タラメ</high>",
                pitch_number="0",
            ),
        ]


class TestAccDictClear:
    """Self-contained test for table clearing."""

    def test_table_clear(
        self,
        tmp_db_connection: Sqlite3Buddy,
        tmp_upd_file: pathlib.Path,
        tmp_user_accents_file: pathlib.Path,
    ) -> None:
        writer = SqliteAccDictWriter(tmp_db_connection, tmp_upd_file, tmp_user_accents_file)
        writer.ensure_sqlite_populated()
        assert writer.is_table_filled() is True
        assert writer.is_table_up_to_date() is True
        writer.clear_table()
        assert writer.is_table_filled() is False
        assert writer.is_table_up_to_date() is False
