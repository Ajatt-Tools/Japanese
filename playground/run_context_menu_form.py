# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.config_view import ContextMenuConfigView
from japanese.widgets.settings_form import ContextMenuSettingsForm
from playground.utils import NoAnkiConfigView


class MockWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self._config = NoAnkiConfigView()
        self._context_menu_config = ContextMenuConfigView(self._config)
        self.form = ContextMenuSettingsForm(self._context_menu_config)
        self.initUI()

    def initUI(self) -> None:
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
