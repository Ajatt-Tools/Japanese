# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
import re
from collections.abc import Iterable
from typing import NamedTuple, Union

from aqt.utils import showInfo, tooltip

from ..ajt_common.utils import ui_translate
from ..pitch_accents.consts import NO_ACCENT
from ..pitch_accents.user_accents import get_tsv_writer, get_user_tsv_reader
from .table import ExpandingTableWidget


def is_comma_separated_list_of_numbers(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9,]+", text))


def is_allowed_accent_notation(text: str) -> bool:
    return is_comma_separated_list_of_numbers(text) or text == NO_ACCENT


class PitchAccentTableRow(NamedTuple):
    headword: str
    kana_reading: str
    pitch_numbers: str


def read_user_tsv_file(f: Iterable[str]) -> Iterable[PitchAccentTableRow]:
    table_rows: dict[PitchAccentTableRow, None] = {}
    for row_dict in get_user_tsv_reader(f, field_names=tuple(PitchAccentTableRow.__annotations__)):
        table_rows[PitchAccentTableRow(**row_dict)] = None
    return table_rows.keys()


def write_user_tsv_file(of, tsv_rows: Iterable[dict[str, str]]) -> None:
    writer = get_tsv_writer(of, field_names=tuple(PitchAccentTableRow.__annotations__))
    writer.writerows(tsv_rows)


class PitchOverrideTable(ExpandingTableWidget):
    """
    Read, display, edit and save the user's pitch accent overrides.

    Note: the user's TSV file is stored "as is",
    but the sqlite database stores everything in katakana.
    The conversion happens when the entries are added to the sqlite database.
    This table preserves the way words are spelled originally.
    """

    _columns = tuple(ui_translate(s) for s in PitchAccentTableRow._fields)
    _sep_regex = re.compile(r"[ \r\t\n.;。、；・]+", flags=re.IGNORECASE | re.MULTILINE)

    def _read_tsv_file(self, file_path: pathlib.Path) -> Iterable[PitchAccentTableRow]:
        try:
            with open(file_path, newline="", encoding="utf-8") as f:
                yield from read_user_tsv_file(f)
        except FileNotFoundError:
            print(f"file doesn't exist: {file_path}")
        except TypeError as ex:
            error = str(ex).replace(".__new__()", "")
            showInfo(f"The file is formatted incorrectly. {error}.", type="warning", parent=self)

    def iterateRowTexts(self) -> Iterable[PitchAccentTableRow]:
        for row_cells in self.iterateRows():
            if all(row_cells):
                yield PitchAccentTableRow(*(cell.text() for cell in row_cells))

    def update_from_tsv(self, file_path: pathlib.Path, reset_table: bool = True):
        table_rows_combined: dict[PitchAccentTableRow, None] = {}
        if not reset_table:
            table_rows_combined.update(dict.fromkeys(self.iterateRowTexts()))
        table_rows_combined.update(dict.fromkeys(self._read_tsv_file(file_path)))
        self.setRowCount(0)
        for row_cells in table_rows_combined:
            if all(row_cells):
                self.addRow(row_cells)
        return self

    def _as_tsv_rows(self) -> Iterable[dict[str, str]]:
        return (
            row_cells._asdict()
            for row_cells in self.iterateRowTexts()
            if all(row_cells) and is_allowed_accent_notation(row_cells.pitch_numbers)
        )

    def dump(self, file_path: Union[pathlib.Path, str]) -> None:
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as of:
                write_user_tsv_file(of, self._as_tsv_rows())
        except OSError as ex:
            showInfo(f"{ex.__class__.__name__}: this file can't be written.", type="warning", parent=self)
