# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
from collections.abc import Collection, Iterable
from typing import NamedTuple

from aqt.qt import *
from aqt.utils import showInfo

from ..ajt_common.utils import ui_translate
from ..pitch_accents.consts import NO_ACCENT
from .table import ExpandingTableWidget


def is_comma_separated_list_of_numbers(text: str):
    return bool(re.fullmatch(r"[0-9,]+", text))


def is_allowed_accent_notation(text: str):
    return is_comma_separated_list_of_numbers(text) or text == NO_ACCENT


class PitchAccentTableRow(NamedTuple):
    word: str
    reading: str
    pitch_number: str


class PitchOverrideTable(ExpandingTableWidget):
    _columns = tuple(ui_translate(s) for s in PitchAccentTableRow._fields)
    _sep_regex = re.compile(r"[ \r\t\n.;。、；・]+", flags=re.IGNORECASE | re.MULTILINE)
    _column_sep = "\t"

    @classmethod
    def from_tsv(cls, file_path: str):
        return cls().update_from_tsv(file_path)

    def read_tsv_file(self, file_path: str) -> Collection[PitchAccentTableRow]:
        table_rows = {}
        try:
            with open(file_path, encoding="utf8") as f:
                try:
                    table_rows.update(
                        dict.fromkeys(PitchAccentTableRow(*line.strip().split(self._column_sep)) for line in f)
                    )
                except TypeError as ex:
                    error = str(ex).replace(".__new__()", "")
                    showInfo(f"The file is formatted incorrectly. {error}.", type="warning", parent=self)
        except FileNotFoundError:
            pass
        return table_rows.keys()

    def iterateRowTexts(self) -> Iterable[PitchAccentTableRow]:
        for row_cells in self.iterateRows():
            if all(row_cells):
                yield PitchAccentTableRow(*(cell.text() for cell in row_cells))

    def update_from_tsv(self, file_path: str, reset_table: bool = True):
        table_rows_combined = dict.fromkeys(
            (
                *(self.iterateRowTexts() if not reset_table else ()),
                *self.read_tsv_file(file_path),
            )
        )
        self.setRowCount(0)
        for row_cells in table_rows_combined:
            if all(row_cells):
                self.addRow(row_cells)
        return self

    def as_tsv_rows(self) -> list[str]:
        return [
            self._column_sep.join(row_cells)
            for row_cells in self.iterateRowTexts()
            if all(row_cells) and is_allowed_accent_notation(row_cells.pitch_number)
        ]

    def dump(self, file_path: str):
        try:
            with open(file_path, "w", encoding="utf8") as of:
                of.write("\n".join(self.as_tsv_rows()))
        except OSError as ex:
            showInfo(f"{ex.__class__.__name__}: this file can't be written.", type="warning", parent=self)
