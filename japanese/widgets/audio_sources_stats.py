# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses

from aqt.qt import *

from ..audio_manager.source_manager import AudioStats, TotalAudioStats

from ..ajt_common.utils import ui_translate


class AudioStatsTable(QTableWidget):
    def __init__(self, parent=None):
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


class AudioStatsDialog(QDialog):
    name = "ajt__audio_stats_dialog"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self: QDialog
        self.setWindowTitle("Audio Statistics")
        self.setMinimumSize(400, 240)
        self.table = AudioStatsTable()
        self.setLayout(QVBoxLayout())
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.layout().addWidget(self.table)
        self.layout().addWidget(self._button_box)
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def load_data(self, stats: TotalAudioStats):
        for idx, row in enumerate(stats.sources):
            self.table.insertRow(idx)
            for jdx, item in enumerate(dataclasses.astuple(row)):
                self.table.setItem(idx, jdx, QTableWidgetItem(str(item)))


def get_mock_stats() -> TotalAudioStats:
    return TotalAudioStats(
        unique_files=23,
        unique_headwords=25,
        sources=[
            AudioStats("tick", 5, 6),
            AudioStats("tack", 7, 7),
            AudioStats("toe", 10, 9),
        ],
    )
