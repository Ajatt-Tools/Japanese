# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from aqt.qt import *

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.widgets.svg_settings import SvgSettingsWidget
from playground.utils import NoAnkiConfigView


class MockWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self._config = NoAnkiConfigView()
        self._svg_config = SvgPitchGraphOptionsConfigView(self._config)
        self._settings_widget = SvgSettingsWidget(self._svg_config)
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle("Settings Form")
        self.setMinimumSize(300, 300)

        layout = QVBoxLayout()
        layout.addWidget(self._settings_widget)
        button = QPushButton("Save")
        layout.addWidget(button)
        qconnect(button.clicked, self.accept)

        self.setLayout(layout)

    def accept(self) -> None:
        # https://doc.qt.io/qt-6/qdialog.html#accept
        print(f"{self._settings_widget.as_dict()=}")
        return super().accept()


def main() -> None:
    app = QApplication(sys.argv)
    form = MockWindow()
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
