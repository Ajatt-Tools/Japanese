# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import typing
from collections.abc import Sequence
from unittest.mock import create_autospec

import pytest
from aqt.qt import QApplication, QWidget

from japanese.pitch_accents.colors import SvgGraphColorMode
from japanese.widgets import webview

BASE_CSS_REF: typing.Final = "base.css"
GRAPH_CSS_REF: typing.Final = "graph.css"
BASE_STYLE_TAG: typing.Final = "<style>base</style>"
GRAPH_STYLE_TAG: typing.Final = "<style>graph</style>"


@pytest.mark.parametrize(
    "color_mode, expected_refs",
    [
        (SvgGraphColorMode.black_and_white, [BASE_CSS_REF]),
        (SvgGraphColorMode.css, [BASE_CSS_REF, GRAPH_CSS_REF]),
        (SvgGraphColorMode.svg_attributes, [BASE_CSS_REF]),
    ],
)
def test_get_css_file_refs(
    monkeypatch: pytest.MonkeyPatch, color_mode: SvgGraphColorMode, expected_refs: Sequence[str]
) -> None:
    """Graph CSS file refs are included only in CSS color mode."""
    monkeypatch.setattr(webview, "ajt_pitch_graph_css", lambda: GRAPH_CSS_REF)

    assert webview.get_css_file_refs(color_mode=color_mode, includes=(BASE_CSS_REF,)) == list(expected_refs)


@pytest.mark.parametrize(
    "color_mode, expected_style_tags",
    [
        (SvgGraphColorMode.black_and_white, (BASE_STYLE_TAG,)),
        (SvgGraphColorMode.css, (BASE_STYLE_TAG, GRAPH_STYLE_TAG)),
        (SvgGraphColorMode.svg_attributes, (BASE_STYLE_TAG,)),
    ],
)
def test_get_css_inline_styles(
    monkeypatch: pytest.MonkeyPatch, color_mode: SvgGraphColorMode, expected_style_tags: Sequence[str]
) -> None:
    """Graph inline CSS is included only in CSS color mode."""
    monkeypatch.setattr(webview, "graphs_inline_css_style_tag", lambda: GRAPH_STYLE_TAG)

    assert webview.get_css_inline_styles(color_mode=color_mode, includes=(BASE_STYLE_TAG,)) == expected_style_tags


class TestZoomableWebViewMixin:
    """Zoom steps change the zoom factor by ZOOM_FACTOR_STEP."""

    def test_zoom_in_out(self, qapp: QApplication) -> None:
        """zoom_in and zoom_out shift the zoom factor by exactly one step."""
        view = webview.ZoomableWebViewMixin()
        initial = view.zoomFactor()
        view.zoom_in()
        assert view.zoomFactor() == pytest.approx(initial + webview.ZOOM_FACTOR_STEP)
        view.zoom_out()
        assert view.zoomFactor() == pytest.approx(initial)


class TestGetSvgPreviewWebview:
    """get_svg_preview_webview selects the Anki or standalone web view implementation."""

    def test_selects_anki_view_when_anki_runs(self, qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
        """When Anki is running, the Anki web view is selected."""
        anki_view = create_autospec(webview.AnkiSVGPreviewWebView, instance=True)
        monkeypatch.setattr(webview, "mw", object())
        monkeypatch.setattr(webview, "AnkiSVGPreviewWebView", lambda *args, **kwargs: anki_view)

        assert webview.get_svg_preview_webview(parent=QWidget(), css_file_names=(), action_name="x") is anki_view

    def test_selects_no_anki_view_outside_anki(self, qapp: QApplication) -> None:
        """Outside Anki, the standalone web view with inlined CSS is selected."""
        assert isinstance(
            webview.get_svg_preview_webview(parent=QWidget(), css_file_names=(), action_name="x"),
            webview.NoAnkiSVGPreviewWebView,
        )

    def test_no_anki_bridge_command_is_noop(self, qapp: QApplication) -> None:
        """The standalone web view accepts bridge-command setup without raising."""
        view = webview.NoAnkiSVGPreviewWebView(css_file_names=(), parent=None)

        assert view.set_bridge_command(lambda cmd: None, object()) is None
