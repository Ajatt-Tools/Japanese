# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.widgets.settings_form import SvgSettingsForm
from tests.run_context_menu_form import NoAnkiConfigView


class MockWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._config = NoAnkiConfigView()
        self._svg_config = SvgPitchGraphOptionsConfigView(NoAnkiConfigView())
        self.form = SvgSettingsForm(self._svg_config)
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

    def accept(self):
        print(f"{self.form.as_dict()=}")
        return super().accept()


def main() -> None:
    app = QApplication(sys.argv)
    form = MockWindow()
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
