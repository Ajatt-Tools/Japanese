# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import random
import typing

from aqt.qt import *

try:
    from ..helpers import ui_translate
    from ..helpers.audio_manager import FileUrlData
    from .audio_sources import SourceEnableCheckbox
except ImportError:
    from helpers import ui_translate
    from helpers.audio_manager import FileUrlData
    from widgets.audio_sources import SourceEnableCheckbox


class AudioManager(typing.Protocol):
    def search_audio(self, src_text: str, split_morphemes: bool) -> list[FileUrlData]:
        ...


class SearchBar(QWidget):
    """
    Combines a line edit and a search button.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_line = QLineEdit()
        self._search_button = QPushButton('Search')
        qconnect(self._search_line.returnPressed, self._search_button.click)
        self._initUI()

    def keyPressEvent(self, evt: QKeyEvent):
        if evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return:
            return
        return super().keyPressEvent(evt)

    @property
    def search_committed(self) -> pyqtSignal:
        return self._search_button.clicked

    def current_text(self):
        return self._search_line.text()

    def set_text(self, text: str):
        self._search_line.setText(text)

    def _initUI(self):
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(3)
        hbox.addWidget(self._search_line)
        hbox.addWidget(self._search_button)
        self.setLayout(hbox)


class SearchResultsTableColumns(enum.Enum):
    add_to_note = 0
    source_name = enum.auto()
    url = enum.auto()
    filename = enum.auto()
    word = enum.auto()

    @classmethod
    def count(cls):
        return sum(1 for _ in cls)


class SearchResultsTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_results: list[FileUrlData] = []
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setColumnCount(SearchResultsTableColumns.count())
        self.setHorizontalHeaderLabels(ui_translate(item.name) for item in SearchResultsTableColumns)
        self.setSectionResizeModes()

    def setSectionResizeModes(self):
        contents = QHeaderView.ResizeMode.ResizeToContents
        stretch = QHeaderView.ResizeMode.Stretch
        hor_header = self.horizontalHeader()

        for column_number in (item.value for item in SearchResultsTableColumns):
            hor_header.setSectionResizeMode(column_number, stretch)
        hor_header.setSectionResizeMode(SearchResultsTableColumns.add_to_note.value, contents)

    def clear(self):
        self.setRowCount(0)
        self._last_results.clear()

    def files_to_add(self) -> list[FileUrlData]:
        to_add = []
        for row_n, result in zip(range(self.rowCount()), self._last_results):
            checkbox = typing.cast(QCheckBox, self.cellWidget(row_n, SearchResultsTableColumns.add_to_note.value))
            if checkbox.isChecked():
                to_add.append(result)
        return to_add

    def populate_with_results(self, results: list[FileUrlData]):
        self._last_results = results
        for row_n, file in enumerate(results):
            self.insertRow(row_n)
            self.setCellWidget(row_n, SearchResultsTableColumns.add_to_note.value, SourceEnableCheckbox())
            row_map = {
                SearchResultsTableColumns.source_name: file.source_name,
                SearchResultsTableColumns.url: file.url,
                SearchResultsTableColumns.filename: file.desired_filename,
                SearchResultsTableColumns.word: file.word,
            }
            for column, field in row_map.items():
                self.setItem(row_n, column.value, item := QTableWidgetItem(field))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)


class AudioSearchDialog(QDialog):
    def __init__(self, audio_manager: AudioManager, parent=None):
        super().__init__(parent)
        self._audio_manager = audio_manager
        self.setMinimumSize(600, 400)
        self.setWindowTitle("Audio search")

        # create widgets
        self._search_bar = SearchBar()
        self._field_selector = QComboBox()
        self._table_widget = SearchResultsTable()
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )

        # add search bar, button, and table to main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(self._create_top_layout())
        main_layout.addWidget(self._table_widget)
        main_layout.addWidget(self._button_box)
        self.setLayout(main_layout)

        # connect search button to search function
        qconnect(self._search_bar.search_committed, self.search)
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def _create_top_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Destination:"))
        layout.addWidget(self._field_selector)
        layout.addWidget(QLabel("Search:"))
        layout.addWidget(self._search_bar)
        self._field_selector.setMinimumWidth(150)
        self._field_selector.setMaximumWidth(200)
        self._field_selector.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        return layout

    @property
    def table(self):
        return self._table_widget

    def set_search_text(self, search_text: str):
        return self._search_bar.set_text(search_text)

    def files_to_add(self):
        return self._table_widget.files_to_add()

    def search(self):
        search_text = self._search_bar.current_text().lower()
        self._table_widget.clear()
        if not search_text:
            return
        # repopulate with new data
        self._table_widget.populate_with_results(self._audio_manager.search_audio(search_text, split_morphemes=True))


def main():
    def get_rand_file():
        import string

        def gen_rand_str(length: int = 10):
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

        return FileUrlData(
            f"https://example.com/{gen_rand_str()}.ogg",
            f"{gen_rand_str()}.ogg",
            gen_rand_str(),
            f"src{gen_rand_str()}")

    class MockAudioManager:
        # noinspection PyMethodMayBeStatic
        # noinspection PyUnusedLocal
        def search_audio(self, src_text: str, split_morphemes: bool) -> list[FileUrlData]:
            """
            Used for testing purposes.
            """
            output = []
            if src_text:
                for _ in range(random.randint(1, 10)):
                    output.append(get_rand_file())
            return output

    app = QApplication(sys.argv)
    dialog = AudioSearchDialog(MockAudioManager())
    dialog.set_search_text("test")
    dialog.search()
    dialog.show()
    app.exec()
    for file in dialog.files_to_add():
        print(file)


if __name__ == '__main__':
    main()
