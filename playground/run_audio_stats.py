# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.audio_manager.basic_types import AudioStats, TotalAudioStats
from japanese.widgets.audio_sources_stats import AudioStatsDialog


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


def main():
    app = QApplication(sys.argv)
    dialog: QDialog = AudioStatsDialog()
    dialog.load_data(get_mock_stats())
    dialog.show()
    app.exec()


if __name__ == "__main__":
    main()
