# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os.path
import re
from typing import Collection, Iterable, NewType, NamedTuple

from aqt.qt import *
from aqt.utils import showInfo

try:
    from ..database.consts import NO_ACCENT
except ImportError:
    from database.consts import NO_ACCENT


def is_ctrl_v_pressed(event: QKeyEvent) -> bool:
    return (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_V)


UNUSED = -1
CellContent = NewType("CellContent", Union[QTableWidgetItem | QWidget])
TableRow = NewType("TableRow", Collection[CellContent])


class ExpandingTableWidget(QTableWidget):
    _columns: Collection[str] = None
    _sep_regex: re.Pattern = None

    def __init__(self, *args):
        super().__init__(*args)
        self.setColumnCount(len(self._columns))
        self.setHorizontalHeaderLabels(self._columns)
        self.addDeleteSelectedRowsContextAction()
        self.addCreateNewRowContextAction()
        self.addPasteContextAction()
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStretchAllColumns()
        qconnect(self.cellChanged, self.onCellChanged)
        self.setRowCount(0)

    def setRowCount(self, rows: int):
        super().setRowCount(rows)
        if rows < 1:
            self.addEmptyLastRow()

    def setStretchAllColumns(self):
        header = self.horizontalHeader()
        for column_number in range(len(self._columns)):
            header.setSectionResizeMode(column_number, QHeaderView.ResizeMode.Stretch)

    def addDeleteSelectedRowsContextAction(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Delete selected rows", self)
        qconnect(action.triggered, self.deleteSelectedRows)
        self.addAction(action)

    def addCreateNewRowContextAction(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Add a new empty row", self)
        qconnect(action.triggered, self.addEmptyLastRow)
        self.addAction(action)

    def addPasteContextAction(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Paste (Ctrl+V)", self)
        qconnect(action.triggered, self.fillCurrentRowFromClipBoard)
        self.addAction(action)

    def deleteSelectedRows(self):
        for index in self.selectedIndexes():
            self.removeRow(index.row())

    def removeRow(self, row: int) -> None:
        """
        The table never stays empty. Empty rows are added at the end if needed.
        """
        super().removeRow(deleted_row := self.currentRow())
        if self.rowCount() < 1 or deleted_row == self.rowCount():
            self.addEmptyLastRow()

    def isCellFilled(self, cell: CellContent) -> bool:
        """
        When dealing with widgets inside cells,
        the table has to take them into account.

        Subclasses must override this method to handle other widgets.
        """
        return bool(cell.text())

    def onCellChanged(self, row_n: int, _col_n: int = UNUSED):
        """
        If the last row is full, add a new row.
        If the row is empty, and it's not last, delete it.
        """

        def is_full_last_row(row: TableRow) -> bool:
            return all(self.isCellFilled(item) for item in row) and row_n == self.rowCount() - 1

        def is_empty_not_last_row(row: TableRow) -> bool:
            return all(not self.isCellFilled(item) for item in row) and self.rowCount() > row_n + 1

        if not all(row_cells := self.getRowCellContents(row_n)):
            return
        elif is_full_last_row(row_cells) or self.rowCount() < 1:
            self.addEmptyLastRow()
        elif is_empty_not_last_row(row_cells):
            self.removeRow(row_n)

    def addRow(self, cells: Iterable[str | QWidget], last: bool = False):
        self.insertRow(row_n := max(0, self.rowCount() if last else self.rowCount() - 1))
        for col_n, cell_content in enumerate(cells):
            self.insertCellContent(row_n, col_n, cell_content)

    def insertCellContent(self, row_n: int, col_n: int, content: str | QWidget):
        """
        Depending on the type of content, either set a new item, or set a cell widget.
        """
        if isinstance(content, str):
            self.setItem(row_n, col_n, QTableWidgetItem(content))
        elif isinstance(content, QWidget):
            self.setCellWidget(row_n, col_n, content)
        else:
            raise ValueError("Invalid parameter passed.")

    def addEmptyLastRow(self):
        return self.addRow(cells=('' for _column in self._columns), last=True)

    def getCellContent(self, row_n: int, col_n: int) -> CellContent | None:
        """
        Return an item inside the cell if there is an item, or a widget if it has been set.
        """
        if (item := self.item(row_n, col_n)) is not None:
            return item
        if (widget := self.cellWidget(row_n, col_n)) is not None:
            return widget

    def getRowCellContents(self, row_n: int) -> TableRow:
        return tuple(self.getCellContent(row_n, col_n) for col_n in range(self.columnCount()))

    def iterateRows(self) -> Iterable[TableRow]:
        for row_number in range(self.rowCount()):
            yield self.getRowCellContents(row_number)

    def fillCurrentRowFromClipBoard(self):
        """
        Takes text from the clipboard, splits it by the defined separators,
        then maps each part to a cell in the current row.
        """

        def text_parts():
            return filter(bool, map(str.strip, re.split(self._sep_regex, QApplication.clipboard().text(), )), )

        def column_iter():
            return range(self.currentColumn(), self.columnCount(), )

        for col_n, text in zip(column_iter(), text_parts()):
            self.fillCellContent(self.currentRow(), col_n, text)

    def fillCellContent(self, row_n: int, col_n: int, content: str):
        try:
            self.getCellContent(row_n, col_n).setText(content)
        except AttributeError:
            pass

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Delete:
            self.removeRow(self.currentRow())
        if is_ctrl_v_pressed(event):
            self.fillCurrentRowFromClipBoard()
        return super().keyPressEvent(event)


def is_comma_separated_list_of_numbers(text: str):
    return bool(re.fullmatch(r'[0-9,]+', text))


def is_allowed_accent_notation(text: str):
    return is_comma_separated_list_of_numbers(text) or text == NO_ACCENT


class PitchAccentTableRow(NamedTuple):
    word: str
    reading: str
    pitch_number: str


class PitchOverrideTable(ExpandingTableWidget):
    _columns = tuple(s.capitalize() for s in PitchAccentTableRow._fields)
    _sep_regex = re.compile(r"[ \r\t\n.;。、；・]+", flags=re.IGNORECASE | re.MULTILINE)
    _column_sep = '\t'

    @classmethod
    def from_tsv(cls, file_path: str, *args):
        return cls(*args).update_from_tsv(file_path)

    def read_tsv_file(self, file_path: str) -> Collection[PitchAccentTableRow]:
        table_rows = {}
        if os.path.isfile(file_path):
            with open(file_path, encoding='utf8') as f:
                try:
                    table_rows.update(dict.fromkeys(
                        PitchAccentTableRow(*line.strip().split(self._column_sep))
                        for line in f
                    ))
                except TypeError as ex:
                    error = str(ex).replace('.__new__()', '')
                    showInfo(f"The file is formatted incorrectly. {error}.", type="warning", parent=self)
        return table_rows.keys()

    def iterateRowTexts(self) -> Iterable[PitchAccentTableRow]:
        for row_cells in self.iterateRows():
            if all(row_cells):
                yield PitchAccentTableRow(*(cell.text() for cell in row_cells))

    def update_from_tsv(self, file_path: str, reset_table: bool = True):
        table_rows_combined = dict.fromkeys((
            *(self.iterateRowTexts() if not reset_table else ()),
            *self.read_tsv_file(file_path),
        ))
        self.setRowCount(0)
        for row_cells in table_rows_combined:
            if all(row_cells):
                self.addRow(row_cells)
        return self

    def as_tsv(self) -> list[str]:
        return [
            self._column_sep.join(row_cells)
            for row_cells in self.iterateRowTexts()
            if all(row_cells) and is_allowed_accent_notation(row_cells.pitch_number)
        ]

    def dump(self, file_path: str):
        try:
            with open(file_path, 'w', encoding='utf8') as of:
                of.write('\n'.join(self.as_tsv()))
        except OSError as ex:
            showInfo(f"{ex.__class__.__name__}: this file can't be written.", type="warning", parent=self)


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.table = PitchOverrideTable(self)
        self.initUI()

    def initUI(self):
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.table)

        # example rows
        self.table.addRow(['咖哩', 'かれー', '0'])
        self.table.addRow(['敷礼', 'しきれい', '0'])
        self.table.addRow(['器量良し', 'きりょうよし', '2'])
        self.table.addRow(['隅に置けない', 'すみにおけない', '1'])
        self.table.addRow(['尾骶骨', 'びていこつ', '2'])
        self.table.addRow(['管水母', 'くだくらげ', '3'])


def main():
    app = QApplication(sys.argv)
    _ex = App()
    _ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
