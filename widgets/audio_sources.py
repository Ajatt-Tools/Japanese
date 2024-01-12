# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import io
import re
import typing
from collections.abc import Iterable

from aqt.qt import *

try:
    from .table import ExpandingTableWidget, CellContent, TableRow
    from ..helpers.audio_manager import AudioSourceConfig, normalize_filename
except ImportError:
    from table import ExpandingTableWidget, CellContent, TableRow
    from helpers.audio_manager import AudioSourceConfig, normalize_filename


class SourceEnableCheckbox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
        QCheckBox {
            margin: 0 auto;
        }
        """)


def tooltip_cache_remove_complete(removed: list[AudioSourceConfig]):
    from aqt.utils import tooltip
    from aqt import mw

    msg = io.StringIO()
    if removed:
        msg.write(f"<b>Removed {len(removed)} cache files:</b>")
        msg.write("<ol>")
        for source in removed:
            msg.write(f"<li>{source.name}</li>")
        msg.write("</ol>")
    else:
        msg.write("No cache files to remove")
    if mw:
        tooltip(msg.getvalue(), period=5000)


class AudioManagerInterface(typing.Protocol):
    def request_new_session(self):
        ...


class AudioSourcesTable(ExpandingTableWidget):
    _columns = tuple(field.name.capitalize() for field in dataclasses.fields(AudioSourceConfig))
    # Slightly tightened the separator regex compared to the pitch override widget
    # since names and file paths can contain a wide range of characters.
    _sep_regex: re.Pattern = re.compile(r"[\r\t\n；;。、・]+", flags=re.IGNORECASE | re.MULTILINE)

    def __init__(self, audio_mgr: AudioManagerInterface, *args):
        super().__init__(*args)
        self._audio_mgr = audio_mgr
        self.addMoveRowContextActions()
        self.addClearCacheContextAction()

        # Override the parent class's section resize modes for some columns.
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def addClearCacheContextAction(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Clear cache for selected sources", self)
        qconnect(action.triggered, self.clearCacheForSelectedSources)
        self.addAction(action)

    def clearCacheForSelectedSources(self):
        """
        Remove cache files for the selected audio sources.
        Missing cache files are skipped.
        """
        removed: list[AudioSourceConfig] = []
        gui_selected_sources = [(selected.name, selected.url) for selected in self.iterateSelectedConfigs()]
        with self._audio_mgr.request_new_session() as session:
            for cached in session.audio_sources:
                if (cached.name, cached.url) in gui_selected_sources:
                    session.db.remove_data(cached.name)
                    removed.append(cached)
                    print(f"Removed cache for source: {cached.name} ({cached.url})")
                else:
                    print(f"Source isn't cached: {cached.name} ({cached.url})")
        tooltip_cache_remove_complete(removed)

    def addMoveRowContextActions(self):
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        def move_current_row(offset: int):
            current_row = self.currentRow()
            current_source_copy = pack_back(self.getRowCellContents(current_row))
            self.removeRow(current_row)
            self.addSource(current_source_copy, index=max(0, min(current_row + offset, self.rowCount() - 1)))

        action = QAction("Move row down", self)
        qconnect(action.triggered, lambda: move_current_row(1))
        self.addAction(action)

        action = QAction("Move row up", self)
        qconnect(action.triggered, lambda: move_current_row(-1))
        self.addAction(action)

        action = QAction("Move row to start", self)
        qconnect(action.triggered, lambda: move_current_row(-self.rowCount()))
        self.addAction(action)

        action = QAction("Move row to end", self)
        qconnect(action.triggered, lambda: move_current_row(self.rowCount()))
        self.addAction(action)

    def isCellFilled(self, cell: CellContent) -> bool:
        # A checked checkbox is considered filled,
        # so the user has to uncheck it to trigger an automatic row deletion.
        return isinstance(cell, QCheckBox) and cell.isChecked() or super().isCellFilled(cell)

    def addSource(self, source: AudioSourceConfig, index: int = None):
        self.addRow((checkbox := SourceEnableCheckbox(), source.name, source.url,), index=index)
        # The checkbox widget has to notify the table widget when its state changes.
        # Otherwise, the table will not automatically add/remove rows.
        qconnect(checkbox.stateChanged, lambda checked: self.onCellChanged(self.currentRow()))
        checkbox.setChecked(source.enabled)

    def addEmptyLastRow(self):
        """ Redefine this method. """
        return self.addSource(AudioSourceConfig(True, "", "", ), index=self.rowCount())

    def iterateConfigs(self) -> Iterable[AudioSourceConfig]:
        """
        Return a list of source config objects. Ensure that names don't clash.
        """
        sources = {}
        for row in self.iterateRows():
            if all(row) and (row := pack_back(row)).is_valid:
                row.name = normalize_filename(row.name)
                while row.name in sources:
                    row.name += '(new)'
                sources[row.name] = row
        return sources.values()

    def iterateSelectedConfigs(self) -> Iterable[AudioSourceConfig]:
        selected_row_numbers = sorted(index.row() for index in self.selectedIndexes())
        for index, config in enumerate(self.iterateConfigs()):
            if index in selected_row_numbers:
                yield config

    def populate(self, sources: Iterable[AudioSourceConfig]):
        self.setRowCount(0)
        for source in sources:
            self.addSource(source)
        return self

    def fillCellContent(self, row_n: int, col_n: int, content: str):
        if isinstance(cell := self.getCellContent(row_n, col_n), QCheckBox):
            return cell.setChecked(any(value in content.lower() for value in ('true', 'yes', 'y')))
        return super().fillCellContent(row_n, col_n, content)


def pack_back(row: TableRow) -> AudioSourceConfig:
    def to_json_compatible(item: CellContent):
        if isinstance(item, QCheckBox):
            return item.isChecked()
        return item.text()

    return AudioSourceConfig(*(to_json_compatible(item) for item in row))


# Debug
##########################################################################


class App(QWidget):
    def __init__(self, parent=None):
        from helpers.audio_manager import init_testing_audio_manager

        super().__init__(parent)
        self.setWindowTitle("Test")
        self.table = AudioSourcesTable(init_testing_audio_manager(), self)
        self.initUI()

    def initUI(self):
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.table)

        # example rows
        self.table.addSource(AudioSourceConfig(True, 'NHK1', '/test/nhk/1.json', ))
        self.table.addSource(AudioSourceConfig(False, 'NHK2', '/test/nhk/2.json', ))
        self.table.addSource(AudioSourceConfig(True, 'NHK3', '/test/nhk/3.json', ))
        self.table.addSource(AudioSourceConfig(False, 'NHK4', '/test/nhk/4.json', ))


def main():
    app = QApplication(sys.argv)
    ex: QWidget = App()
    ex.show()
    app.exec()
    for item in ex.table.iterateConfigs():
        print(item)
    sys.exit()


if __name__ == '__main__':
    main()
