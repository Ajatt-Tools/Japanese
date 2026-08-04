# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence

import pytest

from japanese.pitch_accents.colors import SvgGraphColorMode
from japanese.widgets import webview

BASE_CSS_REF = "base.css"
GRAPH_CSS_REF = "graph.css"
BASE_STYLE_TAG = "<style>base</style>"
GRAPH_STYLE_TAG = "<style>graph</style>"


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
