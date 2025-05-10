# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses

from aqt.qt import *

from ..ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from ..ajt_common.utils import ui_translate
from ..audio_manager.basic_types import AudioStats, TotalAudioStats


class AudioStatsTable(QTableWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self: QTableWidget
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.horizontalHeader().setStretchLastSection(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setColumnCount(len(dataclasses.fields(AudioStats)))
        self.setHorizontalHeaderLabels([ui_translate(field.name) for field in dataclasses.fields(AudioStats)])
        self.setStretchAllColumns()

    def setStretchAllColumns(self):
        header = self.horizontalHeader()
        for column_number in range(self.columnCount()):
            header.setSectionResizeMode(column_number, QHeaderView.ResizeMode.Stretch)


class AudioStatsDialog(AnkiSaveAndRestoreGeomDialog):
    name: str = "ajt__audio_stats_dialog"
    _table: AudioStatsTable
    _button_box: QDialogButtonBox

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self: QDialog
        self.setWindowTitle("Audio Statistics")
        self.setMinimumSize(400, 240)
        self._table = AudioStatsTable()
        self.setLayout(QVBoxLayout())
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.layout().addWidget(self._table)
        self.layout().addWidget(self._button_box)
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def load_data(self, stats: TotalAudioStats) -> "AudioStatsDialog":
        for idx, row in enumerate(stats.sources):
            self._table.insertRow(idx)
            for jdx, item in enumerate(dataclasses.astuple(row)):
                self._table.setItem(idx, jdx, QTableWidgetItem(str(item)))
        return self
