# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from aqt.qt import *

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from japanese.widgets.settings_form import SvgSettingsForm
from tests.run_context_menu_form import NoAnkiConfigView

SHOW_ENTRIES = (
    FormattedEntry(
        "オンガクカ",
        "<low_rise>オ</low_rise><high>ンカ<nasal>&#176;</nasal><devoiced>ク</devoiced>カ</high>",
        "0",
    ),
    FormattedEntry(
        "スウカゲツ",
        "<low_rise>ス</low_rise><high_drop>ウカ</high_drop><low>ゲツ</low>",
        "3",
    ),
)


class MockWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._config = NoAnkiConfigView()
        self._svg_config = SvgPitchGraphOptionsConfigView(NoAnkiConfigView())
        self._form = SvgSettingsForm(self._svg_config)
        self._view = QWebEngineView()
        self._maker = SvgPitchGraphMaker(options=self._svg_config)
        self.initUI()
        self.update_view()
        qconnect(self._form.opts_changed, self.update_view)

    def update_view(self) -> None:
        self._svg_config.update(self._form.as_dict())
        self._view.setHtml(
            """
            <style>
            body {
                display: flex;
                flex-flow: row wrap;
                gap: 5px;
                align-content: flex-start;
            }
            svg {
                display: block;
                border: 1px dotted black;
            }
            </style>
            """
            + "".join(self._maker.make_graph(entry) for entry in SHOW_ENTRIES)
        )

    def initUI(self):
        self.setWindowTitle("Settings Form")
        self.setMinimumSize(300, 300)

        layout = QVBoxLayout()
        layout.addWidget(self._form)
        layout.addWidget(self._view)
        button = QPushButton("Save")
        layout.addWidget(button)
        qconnect(button.clicked, self.accept)

        self.setLayout(layout)

    def accept(self):
        print(f"{self._form.as_dict()=}")
        return super().accept()


def main() -> None:
    app = QApplication(sys.argv)
    form = MockWindow()
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
