# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Any, TypeAlias

from aqt.qt import *
from aqt.webview import AnkiWebView

from ..helpers.webview_utils import (
    ajt_pitch_graph_css,
    ajt_webview_css,
)
from ..helpers.webview_utils import graphs_inline_css_style_tag, webview_inline_css_style_tag
from ..widgets.svg_settings import NoAnkiWebView


def head_content() -> str:
    """Return the HTML <head> content with base CSS for the graph preview page."""
    return '<meta charset="UTF-8" />'


class AnkiPitchAccentsWebView(AnkiWebView):
    """An Anki web view with zoom in/out support for pitch graph previews."""

    _main_css_relpath: str
    _graph_css_relpath: str

    def __init__(self, parent: QWidget | None, title: str) -> None:
        super().__init__(parent=parent, title=title)
        self._main_css_relpath = ajt_webview_css()
        self._graph_css_relpath = ajt_pitch_graph_css()

    def set_svg_graphs(self, graphs_as_html: str) -> None:
        """Set pitch graph preview HTML using Anki's web-exported CSS files."""
        self.stdHtml(
            head=head_content(),
            body=graphs_as_html,
            css=[self._main_css_relpath, self._graph_css_relpath],
        )

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


class NoAnkiPitchAccentsWebView(NoAnkiWebView):
    """A pitch graph preview web view for standalone runs outside Anki."""

    def set_svg_graphs(self, graphs_as_html: str) -> None:
        """Set pitch graph preview HTML with CSS inlined from local files."""
        css_styles = [webview_inline_css_style_tag(), graphs_inline_css_style_tag()]
        self.stdHtml(
            head=head_content() + "".join(css_styles),
            body=graphs_as_html,
        )

    @staticmethod
    def set_bridge_command(_func: Callable[[str], Any], _context: Any) -> None:
        """Do nothing; bridge commands are only available in Anki's web view."""
        print("set_bridge_command not implemented.")

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


PitchAccentsWebView: TypeAlias = AnkiPitchAccentsWebView | NoAnkiPitchAccentsWebView
