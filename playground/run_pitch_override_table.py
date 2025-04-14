# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


from aqt.qt import *

from japanese.widgets.pitch_override_table import PitchOverrideTable
from tests import DATA_DIR


class App(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Test")
        self.table = PitchOverrideTable(self)
        self.initUI()

    def initUI(self):
        self.setMinimumSize(640, 480)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self.table)

        # example rows
        self.table.addRow(["咖哩", "かれー", "0"])
        self.table.addRow(["敷礼", "しきれい", "0"])
        self.table.addRow(["器量良し", "きりょうよし", "2"])
        self.table.addRow(["隅に置けない", "すみにおけない", "1"])
        self.table.addRow(["尾骶骨", "びていこつ", "2"])
        self.table.addRow(["管水母", "くだくらげ", "3"])
        self.table.update_from_tsv(DATA_DIR / "test_user_accents.tsv", reset_table=False)


def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
