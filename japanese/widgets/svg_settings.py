# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView

from ..config_view import SvgPitchGraphOptionsConfigView
from ..pitch_accents.common import FormattedEntry
from ..pitch_accents.svg_graphs import SvgPitchGraphMaker
from .settings_form import SvgSettingsForm

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
    FormattedEntry(
        "ジンセイ",
        "<high_drop>ジ</high_drop><low>ンセイ</low>",
        "1",
    ),
)

STYLE = """
<style>
*,
*::before,
*::after {
    box-sizing: border-box;
    padding: 0;
    margin: 0;
}
body {
    display: flex;
    flex-flow: row wrap;
    gap: 3px;
    padding: 3px;
    margin: 0;
    align-content: flex-start;
    border: 1px dotted gray;
}
svg {
    display: block;
    border: 1px dotted gray;
    max-width: 100%;
}
:root[class~="night-mode"] [fill="black"] {
    fill: white;
}
:root[class~="night-mode"] [stroke="black"] {
    stroke: white;
}
:not(:root[class~="night-mode"]) body {
    background-color: white;
}
</style>
"""


class NoAnkiWebView(QWebEngineView):
    def stdHtml(self, body: str, head: str) -> None:
        return self.setHtml(
            f"""
        <html>
        <head>{head}</head>
        <body>{body}</body>
        </html>
        """
        )


class SvgSettingsWidget(QWidget):
    _web_view: Union[AnkiWebView, NoAnkiWebView]

    def __init__(self, svg_config: SvgPitchGraphOptionsConfigView):
        super().__init__()
        self._svg_config = svg_config
        self._form = SvgSettingsForm(self._svg_config)
        self._web_view = AnkiWebView() if mw else NoAnkiWebView()
        self._maker = SvgPitchGraphMaker(options=self._svg_config)
        self.initUI()
        self.update_view()
        qconnect(self._form.opts_changed, self.update_view)

    def initUI(self):
        layout = QHBoxLayout()
        layout.addWidget(self._form)
        layout.addWidget(self._web_view)
        layout.setStretch(0, 2)
        layout.setStretch(1, 1)
        self.setLayout(layout)

    def update_view(self) -> None:
        self._svg_config.update(self._form.as_dict())
        self._web_view.stdHtml(
            head=f"""
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {STYLE}
            """,
            body=self._make_svgs(),
        )

    def _make_svgs(self) -> str:
        return "".join(self._maker.make_graph(entry) for entry in SHOW_ENTRIES)

    def as_dict(self) -> dict[str, Union[bool, str, int]]:
        return self._form.as_dict()
