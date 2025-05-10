# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
from typing import cast

from aqt.qt import *
from aqt.utils import tooltip

from ..config_view import config_view as cfg
from .anki_style import fix_default_anki_style
from .pitch_override_table import PitchOverrideTable


class PitchOverrideWidget(QWidget):
    _filename_filter = "TSV Files (*.tsv *.csv);; All Files (*.*)"
    _file_path: pathlib.Path
    _table: PitchOverrideTable
    _import_button: QPushButton
    _export_button: QPushButton

    def __init__(self, parent, file_path: pathlib.Path) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._table = PitchOverrideTable()
        self._import_button = QPushButton("Import TSV")
        self._export_button = QPushButton("Export TSV")
        self.init_UI()
        self.connect_buttons()
        fix_default_anki_style(self._table)
        self._table.update_from_tsv(self._file_path)

    def init_UI(self):
        self.setLayout(layout := QGridLayout())
        layout.addWidget(self._table, 0, 0, 1, 2)
        layout.addWidget(self._import_button, 1, 0, 1, 1)
        layout.addWidget(self._export_button, 1, 1, 1, 1)

    def connect_buttons(self):
        def write_tsv_file():
            # noinspection PyArgumentList
            name, mime = QFileDialog.getSaveFileName(
                parent=cast(QWidget, self),
                caption="Save override table as TSV File",
                directory=cfg["last_file_save_location"],
                filter=self._filename_filter,
            )
            if not name:
                return tooltip("Aborted.")
            self._table.dump(name)
            cfg["last_file_save_location"] = name  # may or may not be lost

        def read_tsv_file():
            # noinspection PyArgumentList
            name, mime = QFileDialog.getOpenFileName(
                parent=cast(QWidget, self),
                caption="Load override table from TSV File",
                directory=cfg["last_file_save_location"],
                filter=self._filename_filter,
            )
            if not name:
                return tooltip("Aborted.")
            self._table.update_from_tsv(name, reset_table=False)
            cfg["last_file_save_location"] = name  # may or may not be lost

        qconnect(self._import_button.clicked, read_tsv_file)
        qconnect(self._export_button.clicked, write_tsv_file)

    def save_to_disk(self) -> None:
        self._table.dump(self._file_path)
