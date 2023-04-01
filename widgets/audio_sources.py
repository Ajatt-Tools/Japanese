# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import re
from typing import Iterable

from aqt.qt import *

try:
    from .table import ExpandingTableWidget, CellContent, TableRow
    from ..helpers.audio_manager import AudioSourceConfig
except ImportError:
    from table import ExpandingTableWidget, CellContent, TableRow
    from helpers.audio_manager import AudioSourceConfig


class SourceEnableCheckbox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
        QCheckBox {
            padding: 10px;
        }
        """)


def filter_name(text: str) -> str:
    """
    Since sources' names are used as filenames to store cache files on disk,
    ensure there are no questionable characters that some OSes may panic from.
    """
    return re.sub(r'[\n\t\r#%&{}<>*?/$!\'":@+`|=]+', ' ', text, flags=re.MULTILINE).strip()


class AudioSourcesTable(ExpandingTableWidget):
    _columns = tuple(field.name.capitalize() for field in dataclasses.fields(AudioSourceConfig))
    # Slightly tightened the separator regex compared to the pitch override widget
    # since names and file paths can contain a wide range of characters.
    _sep_regex: re.Pattern = re.compile(r"[\r\t\n；;。、・]+", flags=re.IGNORECASE | re.MULTILINE)

    def isCellFilled(self, cell: CellContent) -> bool:
        # A checked checkbox is considered filled,
        # so the user has to uncheck it to trigger an automatic row deletion.
        return isinstance(cell, QCheckBox) and cell.isChecked() or super().isCellFilled(cell)

    def addSource(self, source: AudioSourceConfig, last: bool = False):
        self.addRow((source.name, source.url, checkbox := SourceEnableCheckbox()), last=last)
        # The checkbox widget has to notify the table widget when its state changes.
        # Otherwise, the table will not automatically add/remove rows.
        qconnect(checkbox.stateChanged, lambda checked: self.onCellChanged(self.currentRow()))
        checkbox.setChecked(source.enabled)

    def addEmptyLastRow(self):
        """ Redefine this method. """
        return self.addSource(AudioSourceConfig("My audio", "", True), last=True)

    def iterateConfigs(self) -> Iterable[AudioSourceConfig]:
        """
        Return a list of source config objects. Ensure that names don't clash.
        """
        sources = {}
        for row in self.iterateRows():
            if all(row) and (row := pack_back(row)).is_valid:
                row.name = filter_name(row.name)
                while row.name in sources:
                    row.name += '(new)'
                sources[row.name] = row
        return sources.values()

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


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.table = AudioSourcesTable(self)
        self.initUI()

    def initUI(self):
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.table)

        # example rows
        self.table.addSource(AudioSourceConfig('NHK1', '/test/nhk/1.json', True))
        self.table.addSource(AudioSourceConfig('NHK2', '/test/nhk/2.json', False))
        self.table.addSource(AudioSourceConfig('NHK3', '/test/nhk/3.json', True))
        self.table.addSource(AudioSourceConfig('NHK4', '/test/nhk/4.json', False))


def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    app.exec()
    for item in ex.table.iterateConfigs():
        print(item)
    sys.exit()


if __name__ == '__main__':
    main()
