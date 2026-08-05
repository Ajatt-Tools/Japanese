# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence
from typing import Any, TypeAlias

from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView

from ..helpers.debug_log import get_logger
from ..helpers.webview_utils import (
    ajt_pitch_graph_css,
    graphs_inline_css_style_tag,
    head_content,
    inline_css_style_tag,
    web_css_relpath,
)
from ..pitch_accents.colors import SvgGraphColorMode
from ..widgets.common import NoAnkiWebView

logger = get_logger()


def get_css_file_refs(color_mode: SvgGraphColorMode, includes: Sequence[str]) -> list[str]:
    """Return CSS files needed for the selected color mode."""
    match color_mode:
        case SvgGraphColorMode.css:
            return [*includes, ajt_pitch_graph_css()]
        case _:
            return [*includes]


def get_css_inline_styles(color_mode: SvgGraphColorMode, includes: Sequence[str]) -> Sequence[str]:
    """Return inline CSS style tags needed for the selected color mode."""
    match color_mode:
        case SvgGraphColorMode.css:
            return *includes, graphs_inline_css_style_tag()
        case _:
            return (*includes,)


class AnkiSVGPreviewWebView(AnkiWebView):
    """Web view for the pitch accent lookup dialog when Anki is running."""

    def __init__(self, action_name: str, css_file_names: Sequence[str], parent: QWidget | None) -> None:
        super().__init__(parent=parent, title=action_name)
        self._css_file_names = css_file_names

    def set_formatted_html(self, formatted_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set the lookup result page using Anki's web-exported CSS files."""
        self.stdHtml(
            head=head_content(),
            body=formatted_html,
            css=get_css_file_refs(
                color_mode=color_mode, includes=tuple(web_css_relpath(file_name) for file_name in self._css_file_names)
            ),
        )

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


class NoAnkiSVGPreviewWebView(NoAnkiWebView):
    """Web view for the pitch accent lookup dialog in standalone runs (playground, tests)."""

    def __init__(self, css_file_names: Sequence[str], parent: QWidget | None):
        super().__init__(parent)
        self._css_file_names = css_file_names

    def set_formatted_html(self, formatted_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set the lookup result page with CSS inlined from local files."""
        inline_styles = get_css_inline_styles(
            color_mode=color_mode, includes=tuple(inline_css_style_tag(file_name) for file_name in self._css_file_names)
        )
        self.stdHtml(
            head=head_content() + "".join(inline_styles),
            body=formatted_html,
        )

    @staticmethod
    def set_bridge_command(_func: Callable[[str], Any], _context: Any) -> None:
        """Do nothing; bridge commands are only available in Anki's web view."""
        logger.info("set_bridge_command not implemented.")

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


SVGPreviewWebView: TypeAlias = AnkiSVGPreviewWebView | NoAnkiSVGPreviewWebView


def get_svg_preview_webview(parent: QWidget, css_file_names: Sequence[str], action_name: str) -> SVGPreviewWebView:
    """Return the Anki or standalone web view for the lookup dialog."""
    if mw:
        return AnkiSVGPreviewWebView(action_name, css_file_names, parent)
    # Anki isn't running.
    return NoAnkiSVGPreviewWebView(css_file_names, parent)
