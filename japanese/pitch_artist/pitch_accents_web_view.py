# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib
from collections.abc import Callable
from typing import Any, TypeAlias

from aqt.webview import AnkiWebView
from PyQt6.QtWidgets import QWidget

from ..helpers.file_ops import find_file_in_parents
from ..helpers.webview_utils import (
    AJT_WEBVIEW_CSS_FILE_NAME,
    PITCH_GRAPH_CSS_FILE_NAME,
    ajt_pitch_graph_css,
    ajt_webview_css,
)
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
    def set_svg_graphs(self, graphs_as_html: str) -> None:
        css_files = [
            find_file_in_parents(f"web/{AJT_WEBVIEW_CSS_FILE_NAME}"),
            find_file_in_parents(f"web/{PITCH_GRAPH_CSS_FILE_NAME}"),
        ]
        css_rules = "".join(f"<style>{pathlib.Path(file).read_text(encoding='utf-8')}</style>" for file in css_files)
        self.stdHtml(
            head=head_content() + css_rules,
            body=graphs_as_html,
        )

    def set_bridge_command(self, _func: Callable[[str], Any], _context: Any) -> None:
        print("set_bridge_command not implemented.")

    def zoom_in(self) -> None:
        """Increase the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() + 0.1)

    def zoom_out(self) -> None:
        """Decrease the zoom factor by 0.1."""
        self.setZoomFactor(self.zoomFactor() - 0.1)


PitchAccentsWebView: TypeAlias = AnkiPitchAccentsWebView | NoAnkiPitchAccentsWebView
