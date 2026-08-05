# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from japanese.helpers.webview_utils import graphs_inline_css_style_tag
from japanese.pitch_artist.pitch_graph import SvgPitchArtistGraphMaker
from playground.utils import NoAnkiConfigView

CSS_INLINE = """
<style>
body {
    box-sizing: border-box;
    font-size: 25px;
    font-family: "Noto Serif",
        "Noto Serif CJK JP",
        "Yu Mincho",
        "Liberation Serif",
        "Times New Roman",
        Times,
        Georgia,
        Serif;
    background-color: #FFFAF0;
    color: #2A1B0A;
    line-height: 1.4;
    text-align: left;

    display: grid;
    grid-template-columns: max-content max-content;
    row-gap: 8px;
    column-gap: 8px;
}
svg {
    border: 1px solid pink;
    display: block;
}
</style>
"""
CSS_INLINE_GRAPHS = graphs_inline_css_style_tag()

def html_page(body_content: str) -> str:
    """Wrap body content in a full HTML page with pitch graph CSS styles."""
    head_content = """
    <meta charset="UTF-8" />
    <title>Pronunciations</title>
    """
    style = f"{CSS_INLINE}{CSS_INLINE_GRAPHS}"
    return f"<!DOCTYPE html><html><head>{head_content}{style}</head><body>{body_content}</body></html>"


def main() -> None:
    """Launch a Qt window displaying sample pitch accent graphs for testing."""
    sentence = """
    大物[おおもの];2 ; まで;1
    じんせい;1 | まで;1
    じんせい;1 ; まで;a-1
    つかう; , つかった;-
    稼[かせ]いで;k2. がっこう;
    がっこう;1. つくった;2.
    君[dきdみ]; dの 嘘[dうdそ];1 dを.
    自分[じぶん]; じゃ | できない;k2.
    ひとり;1-
    ひとり;2-
    ひとり;3-
    よねん; ぐらい;pa
    よねん; ぐらい;po1
    """

    app = QApplication(sys.argv)
    cfg = NoAnkiConfigView()
    gen = SvgPitchArtistGraphMaker(cfg)

    widget = QWidget()
    widget.setMinimumSize(320, 240)
    layout = QVBoxLayout()
    webview = QWebEngineView(parent=widget)
    layout.addWidget(webview)
    webview.setHtml(html_page("".join(gen.make_graphs(gen.make_sequences(sentence)))))
    widget.setLayout(layout)
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
