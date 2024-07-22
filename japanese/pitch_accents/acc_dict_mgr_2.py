# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import pathlib
import typing

from aqt import mw
from aqt.operations import QueryOp

from ..helpers.file_ops import rm_file, touch
from ..helpers.sqlite3_buddy import Sqlite3Buddy
from ..mecab_controller.kana_conv import to_katakana
from .common import AccDictProvider, AccDictRawTSVEntry, FormattedEntry, get_tsv_reader
from .consts import (
    FORMATTED_ACCENTS_TSV,
    FORMATTED_ACCENTS_UPDATED,
    RES_DIR_PATH,
    USER_DATA_CSV_PATH,
)
from .user_accents import iter_user_formatted_rows


class SqliteAccDictWriter:
    _db: Sqlite3Buddy
    _upd_file: pathlib.Path = FORMATTED_ACCENTS_UPDATED
    _bundled_tsv_file: pathlib.Path = FORMATTED_ACCENTS_TSV
    _user_accents_file: pathlib.Path = USER_DATA_CSV_PATH

    def __init__(
        self,
        db: Sqlite3Buddy,
        upd_file: typing.Optional[pathlib.Path] = None,
        user_accents_file: typing.Optional[pathlib.Path] = None,
    ) -> None:
        self._db = db
        self._upd_file = upd_file or self._upd_file
        self._user_accents_file = user_accents_file or self._user_accents_file
        if not os.path.isdir(RES_DIR_PATH):
            raise OSError("Pitch accents folder is missing!")

    def is_table_up_to_date(self) -> bool:
        return self._upd_file.is_file() and self.is_upd_file_newer()

    def is_upd_file_newer(self) -> bool:
        return os.path.getmtime(self._upd_file) > os.path.getmtime(self._bundled_tsv_file)

    def table_filled(self) -> bool:
        return self._db.get_pitch_accents_headword_count() > 0

    def write_rows(self, rows: typing.Iterable[AccDictRawTSVEntry]) -> None:
        return self._db.insert_pitch_accent_data(rows, AccDictProvider.bundled)

    def write_user_rows(self, rows: typing.Iterable[AccDictRawTSVEntry]) -> None:
        return self._db.insert_pitch_accent_data(rows, AccDictProvider.user)

    def fill_bundled_data(self) -> None:
        return self.write_rows(iter_formatted_rows(self._bundled_tsv_file))

    def clear_user_data(self) -> None:
        self._db.clear_pitch_accents(AccDictProvider.user)

    def fill_user_data(self) -> None:
        return self.write_user_rows(iter_user_formatted_rows(self._user_accents_file))

    def clear_table(self) -> None:
        self._db.clear_pitch_accents_table()
        self.mark_table_old()

    def recreate_table(self) -> None:
        self._db.delete_pitch_accents_table()
        self._db.prepare_pitch_accents_table()
        self.mark_table_old()

    def mark_table_old(self) -> None:
        rm_file(self._upd_file)
        print("Marked pitch accent data as NOT up to date")

    def mark_table_updated(self) -> None:
        touch(self._upd_file)
        print("Marked pitch accent data as up to date.")

    def is_db_ready(self) -> bool:
        return self.table_filled() and self.table_up_to_date()

    def ensure_sqlite_populated(self) -> None:
        if self.is_db_ready():
            return
        print("The pitch accent table needs updating.")
        self.clear_table()
        self.fill_bundled_data()
        self.fill_user_data()
        self.mark_table_updated()


def iter_formatted_rows(tsv_file_path: pathlib.Path) -> typing.Iterable[AccDictRawTSVEntry]:
    """
    Read the formatted pitch accents file to memory.

    Example entry as it appears in the formatted file:
    新年会 シンネンカイ <low_rise>シ</low_rise><high_drop>ンネ</high_drop><low>ンカイ</low> 3
    """
    row: AccDictRawTSVEntry
    with open(tsv_file_path, newline="", encoding="utf-8") as f:
        yield from get_tsv_reader(f)


class SqliteAccDictReader:
    _db: Sqlite3Buddy

    def __init__(self, db: Sqlite3Buddy) -> None:
        self._db = db

    def look_up(self, expr: str) -> typing.Sequence[FormattedEntry]:
        return [
            FormattedEntry(*row)
            for row in self._db.search_pitch_accents(expr, prefer_provider_name=AccDictProvider.user)
        ]


class AccentDictManager2:
    _db_path: typing.Optional[pathlib.Path] = None
    _upd_file: typing.Optional[pathlib.Path] = None
    _user_accents_file: typing.Optional[pathlib.Path] = None

    def __init__(
        self,
        db_path: typing.Optional[pathlib.Path] = None,
        upd_file_path: typing.Optional[pathlib.Path] = None,
        user_accents_path: typing.Optional[pathlib.Path] = None,
    ) -> None:
        self._db_path = db_path or self._db_path
        self._upd_file = upd_file_path or self._upd_file
        self._user_accents_file = user_accents_path or self._user_accents_file

    def mk_writer(self, db: Sqlite3Buddy):
        return SqliteAccDictWriter(db, upd_file=self._upd_file, user_accents_file=self._user_accents_file)

    def lookup(self, expr: str) -> typing.Optional[typing.Sequence[FormattedEntry]]:
        """
        Look up expr in accent db, always as katakana.
        Return None if there's no pitch accent for expr.
        """
        with Sqlite3Buddy(self._db_path) as db:
            reader = SqliteAccDictReader(db)
            return reader.look_up(to_katakana(expr))

    def is_ready(self) -> bool:
        with Sqlite3Buddy(self._db_path) as db:
            writer = self.mk_writer(db)
            return writer.is_db_ready()

    def _ensure_sqlite_populated(self) -> None:
        with Sqlite3Buddy(self._db_path) as db:
            writer = self.mk_writer(db)
            writer.ensure_sqlite_populated()

    def ensure_dict_ready(self) -> None:
        """Ensures that the sqlite3 table is filled with pitch accent data."""
        assert mw

        QueryOp(
            parent=mw,
            op=lambda collection: self._ensure_sqlite_populated(),
            success=lambda _: None,
        ).without_collection().with_progress(
            "Reloading pitch accent dictionary...",
        ).run_in_background()

    def ensure_dict_ready_on_main(self):
        assert not mw
        self._ensure_sqlite_populated()

    def reload_user_accents_from_disk(self) -> None:
        with Sqlite3Buddy(self._db_path) as db:
            writer = self.mk_writer(db)
            writer.clear_user_data()
            writer.fill_user_data()
