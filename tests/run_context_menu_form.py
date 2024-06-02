# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json

from aqt.qt import *

from japanese.ajt_common.addon_config import AddonConfigABC
from japanese.config_view import ContextMenuConfigView
from japanese.helpers.file_ops import find_config_json
from japanese.widgets.settings_form import ContextMenuSettingsForm


class NoAnkiConfigView(AddonConfigABC):
    def __init__(self):
        with open(find_config_json()) as f:
            self._config = json.load(f)

    @property
    def config(self) -> dict:
        return self._config

    @property
    def default_config(self) -> dict:
        return self._config


class MockWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._config = ContextMenuConfigView(NoAnkiConfigView())
        self.form = ContextMenuSettingsForm(self._config)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Settings Form")
        self.setMinimumSize(300, 300)

        layout = QVBoxLayout()
        layout.addWidget(self.form)
        button = QPushButton("Save")
        layout.addWidget(button)
        qconnect(button.clicked, self.accept)

        self.setLayout(layout)


def main() -> None:
    app = QApplication(sys.argv)
    form = MockWindow()
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
