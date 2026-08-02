# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence
from typing import Any, TypeAlias

from aqt.qt import *
from aqt.webview import AnkiWebView

from ..helpers.webview_utils import (
    ajt_pitch_graph_css,
    ajt_webview_css,
    graphs_inline_css_style_tag,
    webview_inline_css_style_tag,
)
from ..pitch_accents.colors import SvgGraphColorMode
from ..widgets.svg_settings import NoAnkiWebView


def head_content() -> str:
    """Return the HTML <head> content with base CSS for the graph preview page."""
    return '<meta charset="UTF-8" />'


def get_css_file_refs(color_mode: SvgGraphColorMode) -> list[str]:
    """Return CSS files needed for the selected color mode."""
    match color_mode:
        case SvgGraphColorMode.css:
            return [ajt_webview_css(), ajt_pitch_graph_css()]
        case _:
            return [ajt_webview_css()]


class AnkiPitchAccentsWebView(AnkiWebView):
    """An Anki web view with zoom in/out support for pitch graph previews."""

    def __init__(self, parent: QWidget | None, title: str) -> None:
        super().__init__(parent=parent, title=title)

    def set_svg_graphs(self, graphs_as_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set pitch graph preview HTML using Anki's web-exported CSS files."""
        self.stdHtml(
            head=head_content(),
            body=graphs_as_html,
            css=get_css_file_refs(color_mode),
        )

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


def get_css_inline_styles(color_mode: SvgGraphColorMode) -> Sequence[str]:
    """Return CSS files needed for the selected color mode."""
    match color_mode:
        case SvgGraphColorMode.css:
            return webview_inline_css_style_tag(), graphs_inline_css_style_tag()
        case _:
            return (webview_inline_css_style_tag(),)


class NoAnkiPitchAccentsWebView(NoAnkiWebView):
    """A pitch graph preview web view for standalone runs outside Anki."""

    def set_svg_graphs(self, graphs_as_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set pitch graph preview HTML with CSS inlined from local files."""
        self.stdHtml(
            head=head_content() + "".join(get_css_inline_styles(color_mode)),
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
