# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Optional

from aqt.qt import QWidget

from ..ajt_common.stats_table_dialog import StatsDialog
from ..ajt_common.utils import ui_translate
from ..audio_manager.basic_types import AudioStats, TotalAudioStats


class AudioStatsDialog(StatsDialog):
    name: str = "ajt__audio_stats_dialog"
    win_title: str = "Audio Statistics"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent=parent,
            column_names=[ui_translate(field.name) for field in dataclasses.fields(AudioStats)],
        )
        self.setMinimumSize(400, 240)

    def load_data(self, stats: TotalAudioStats) -> "AudioStatsDialog":
        super().load_data([dataclasses.astuple(row) for row in stats.sources])
        return self
