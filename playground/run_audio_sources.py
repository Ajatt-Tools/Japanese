# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.audio_manager.basic_types import AudioSourceConfig, NameUrlSet
from japanese.widgets.audio_sources import AudioSourcesTable
from playground.utils import persistent_sqlite3_db_path


def on_remove_selected_sources_clicked(sources: NameUrlSet):
    print(f"remove selected:")
    for source in sources:
        print(f"  {source}")


class App(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.table = AudioSourcesTable(self)
        self.init_ui()

    def init_ui(self) -> None:
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.table)

        # example rows
        self.table.addSource(AudioSourceConfig(True, "NHK1", "/test/nhk/1.json"))
        self.table.addSource(AudioSourceConfig(False, "NHK2", "/test/nhk/2.json"))
        self.table.addSource(AudioSourceConfig(True, "NHK3", "/test/nhk/3.json"))
        self.table.addSource(AudioSourceConfig(False, "NHK4", "/test/nhk/4.json"))

        qconnect(self.table.remove_requested, on_remove_selected_sources_clicked)


def main():
    with persistent_sqlite3_db_path() as db_path:
        app = QApplication(sys.argv)
        ex = App(db_path)
        ex.show()
        app.exec()
        for item in ex.table.iterateConfigs():
            print(item)
        sys.exit()


if __name__ == "__main__":
    main()
