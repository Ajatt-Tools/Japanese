# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.widgets.audio_sources_stats import AudioStatsDialog, get_mock_stats


def main():
    app = QApplication(sys.argv)
    dialog: QDialog = AudioStatsDialog()
    dialog.load_data(get_mock_stats())
    dialog.show()
    app.exec()


if __name__ == "__main__":
    main()
