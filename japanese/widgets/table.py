# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from collections.abc import Collection, Iterable, Sequence
from typing import Optional

from aqt.qt import *


def is_ctrl_v_pressed(event: QKeyEvent) -> bool:
    return (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and (event.key() == Qt.Key.Key_V)


UNUSED = -1
CellContent = Union[QTableWidgetItem, QWidget]
TableRow = Sequence[CellContent]


class ExpandingTableWidget(QTableWidget):
    _columns: Collection[str]
    _sep_regex: re.Pattern

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
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

    def setRowCount(self, rows: int) -> None:
        super().setRowCount(rows)
        if rows < 1:
            self.addEmptyLastRow()

    def setStretchAllColumns(self) -> None:
        header = self.horizontalHeader()
        assert header
        for column_number in range(len(self._columns)):
            header.setSectionResizeMode(column_number, QHeaderView.ResizeMode.Stretch)

    def addDeleteSelectedRowsContextAction(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Delete selected rows", self)
        qconnect(action.triggered, self.deleteSelectedRows)
        self.addAction(action)

    def addCreateNewRowContextAction(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Add a new empty row", self)
        qconnect(action.triggered, self.addEmptyLastRow)
        self.addAction(action)

    def addPasteContextAction(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Paste (Ctrl+V)", self)
        qconnect(action.triggered, self.fillCurrentRowFromClipBoard)
        self.addAction(action)

    def deleteSelectedRows(self) -> None:
        for row_n in reversed(sorted(index.row() for index in self.selectedIndexes())):
            self.removeRow(row_n)

    def removeRow(self, del_row_n: int) -> None:
        """
        The table never stays empty. Empty rows are added at the end if needed.
        """
        super().removeRow(del_row_n)
        if self.rowCount() < 1 or del_row_n == self.rowCount():
            self.addEmptyLastRow()

    def isCellFilled(self, cell: CellContent) -> bool:
        """
        When dealing with widgets inside cells,
        the table has to take them into account.

        Subclasses must override this method to handle other widgets.
        """
        return bool(cell.text())

    def is_last_row(self, row_n: int) -> bool:
        return row_n == self.rowCount() - 1

    def onCellChanged(self, row_n: int, _col_n: int = UNUSED) -> None:
        """
        If the last row is full, add a new row.
        If the row is empty, and it's not last, delete it.
        """

        def is_full_last_row(row: TableRow) -> bool:
            return all(self.isCellFilled(item) for item in row) and self.is_last_row(row_n)

        def is_empty_not_last_row(row: TableRow) -> bool:
            return all(not self.isCellFilled(item) for item in row) and not self.is_last_row(row_n)

        if not all(row_cells := self.getRowCellContents(row_n)):
            return
        elif is_full_last_row(row_cells) or self.rowCount() < 1:
            self.addEmptyLastRow()
        elif is_empty_not_last_row(row_cells):
            self.removeRow(row_n)

    def addRow(self, cells: Iterable[Union[str, QWidget]], row_idx: Optional[int] = None) -> None:
        if row_idx is None:
            # Insert before the last row, since the last row is always an empty row for new data.
            row_idx = self.rowCount() - 1
        self.insertRow(row_n := max(0, row_idx))
        for col_n, cell_content in enumerate(cells):
            self.insertCellContent(row_n, col_n, cell_content)

    def insertCellContent(self, row_n: int, col_n: int, content: Union[str, QWidget]) -> None:
        """
        Depending on the type of content, either set a new item, or set a cell widget.
        """
        if isinstance(content, str):
            self.setItem(row_n, col_n, QTableWidgetItem(content))
        elif isinstance(content, QWidget):
            self.setCellWidget(row_n, col_n, content)
        else:
            raise ValueError("Invalid parameter passed.")

    def addEmptyLastRow(self) -> None:
        return self.addRow(cells=("" for _column in self._columns), row_idx=self.rowCount())

    def getCellContent(self, row_n: int, col_n: int) -> Optional[CellContent]:
        """
        Return an item inside the cell if there is an item, or a widget if it has been set.
        """
        if (item := self.item(row_n, col_n)) is not None:
            return item
        if (widget := self.cellWidget(row_n, col_n)) is not None:
            return widget
        return None

    def getRowCellContents(self, row_n: int) -> TableRow:
        return tuple(self.getCellContent(row_n, col_n) for col_n in range(self.columnCount()))

    def iterateRows(self) -> Iterable[TableRow]:
        for row_number in range(self.rowCount()):
            yield self.getRowCellContents(row_number)

    def fillCurrentRowFromClipBoard(self) -> None:
        """
        Takes text from the clipboard, splits it by the defined separators,
        then maps each part to a cell in the current row.
        """

        def text_parts():
            return filter(bool, map(str.strip, re.split(self._sep_regex, QApplication.clipboard().text())))

        def column_iter():
            return range(self.currentColumn(), self.columnCount())

        for col_n, text in zip(column_iter(), text_parts()):
            self.fillCellContent(self.currentRow(), col_n, text)

    def fillCellContent(self, row_n: int, col_n: int, content: str) -> None:
        try:
            self.getCellContent(row_n, col_n).setText(content)
        except AttributeError:
            pass

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # https://doc.qt.io/qt-6/qdialog.html#keyPressEvent
        if event.key() == Qt.Key.Key_Delete:
            self.removeRow(self.currentRow())
        if is_ctrl_v_pressed(event):
            self.fillCurrentRowFromClipBoard()
        return super().keyPressEvent(event)
