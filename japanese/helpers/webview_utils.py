# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import functools

from aqt import mw

from .file_ops import find_file_in_parents

AJT_WEBVIEW_CSS_FILE_NAME = "ajt_webview.css"
PITCH_GRAPH_CSS_FILE_NAME = "ajt_pitch_graph.css"


@functools.cache
def anki_addon_set_web_exports() -> None:
    assert mw, "Anki must be initialized."
    mw.addonManager.setWebExports(__name__, r"(img|web)/.*\.(js|css|html|png|svg)$")


@functools.cache
def anki_addon_web_relpath() -> str:
    assert mw, "Anki must be initialized."
    return f"/_addons/{mw.addonManager.addonFromModule(__name__)}/web"


@functools.cache
def ajt_webview_css() -> str:
    """Return the web-exported path to the shared AJT webview CSS file."""
    return f"{anki_addon_web_relpath()}/{AJT_WEBVIEW_CSS_FILE_NAME}"


@functools.cache
def ajt_pitch_graph_css() -> str:
    """Return the web-exported path to the shared pitch graph CSS file."""
    return f"{anki_addon_web_relpath()}/{PITCH_GRAPH_CSS_FILE_NAME}"


@functools.cache
def inline_css_style_tag(css_file_name: str) -> str:
    """Return the CSS stylesheet."""
    css = find_file_in_parents(f"web/{css_file_name}").read_text(encoding="utf-8")
    return f"<style>\n{css}\n</style>"


def graphs_inline_css_style_tag() -> str:
    """Return the CSS stylesheet for styling pitch accent SVG graphs."""
    return inline_css_style_tag(PITCH_GRAPH_CSS_FILE_NAME)


def webview_inline_css_style_tag() -> str:
    """Return the CSS stylesheet for styling pitch accent SVG graphs."""
    return inline_css_style_tag(AJT_WEBVIEW_CSS_FILE_NAME)
