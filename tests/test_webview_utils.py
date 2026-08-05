# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable
from unittest.mock import MagicMock

import pytest

from japanese.helpers import webview_utils
from japanese.helpers.consts import META_CHARSET, META_VIEWPORT
from japanese.helpers.file_ops import find_file_in_parents
from japanese.helpers.webview_utils import (
    AJT_SVG_SETTINGS_CSS_FILE_NAME,
    head_content,
    inline_css_style_tag,
    web_css_relpath,
)


@pytest.fixture
def cleared_webview_caches() -> Iterable[None]:
    """Clear the functools caches of webview_utils before and after a test."""
    webview_utils.anki_addon_web_relpath.cache_clear()
    webview_utils.web_css_relpath.cache_clear()
    yield
    webview_utils.anki_addon_web_relpath.cache_clear()
    webview_utils.web_css_relpath.cache_clear()


def test_head_content_returns_meta_tags() -> None:
    """head_content returns the viewport and charset meta tags."""
    assert head_content() == f"{META_VIEWPORT}{META_CHARSET}"


def test_inline_css_style_tag_reads_web_file() -> None:
    """inline_css_style_tag inlines a local CSS file into a <style> tag."""
    css = find_file_in_parents(f"web/{AJT_SVG_SETTINGS_CSS_FILE_NAME}").read_text(encoding="utf-8")
    assert inline_css_style_tag(AJT_SVG_SETTINGS_CSS_FILE_NAME) == f"<style>\n{css}\n</style>"


def test_web_css_relpath(cleared_webview_caches: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """web_css_relpath prefixes the CSS file name with the add-on's web-export path."""
    fake_mw = MagicMock()
    fake_mw.addonManager.addonFromModule.return_value = "japanese"
    monkeypatch.setattr(webview_utils, "mw", fake_mw)

    assert web_css_relpath("x.css") == "/_addons/japanese/web/x.css"
