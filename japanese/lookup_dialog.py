# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import io
from collections import OrderedDict
from collections.abc import Sequence
from gettext import gettext as _
from typing import final

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from .ajt_common.about_menu import menu_root_entry, tweak_window
from .ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from .config_view import LookupDialogPitchOutputFormat
from .config_view import config_view as cfg
from .database.sqlite3_buddy import Sqlite3Buddy
from .helpers.consts import ADDON_NAME
from .helpers.tokens import clean_furigana
from .helpers.webview_utils import anki_addon_web_relpath
from .mecab_controller import to_hiragana
from .pitch_accents.common import AccentDict, FormattedEntry, OrderedSet
from .pitch_accents.styles import HTMLPitchPatternStyle
from .reading import format_pronunciations, lookup, svg_graph_maker, update_html

ACTION_NAME = "Pitch Accent lookup"


def html_style() -> HTMLPitchPatternStyle:
    style = cfg.pitch_accent.html_style
    if style is HTMLPitchPatternStyle.none:
        # 'none' can't be selected here because it is intended for anki card customization.
        return HTMLPitchPatternStyle.u_biq_color_coded
    return style


def get_notation(entry: FormattedEntry, mode: LookupDialogPitchOutputFormat) -> str:
    if mode == LookupDialogPitchOutputFormat.html:
        return (
            f'<span class="pitch_html">{update_html(entry, pitch_accent_style=html_style())}</span>'
            f" {entry.pitch_number_html}"
        )
    elif mode == LookupDialogPitchOutputFormat.svg:
        return f"{svg_graph_maker.make_graph(entry)} {entry.pitch_number_html}"
    raise RuntimeError("Unreachable.")


def entries_to_html(entries: Sequence[FormattedEntry]) -> OrderedSet[str]:
    return OrderedSet(get_notation(entry, mode=cfg.pitch_accent.lookup_pitch_format) for entry in entries)


@final
class ViewPitchAccentsDialog(AnkiSaveAndRestoreGeomDialog):
    name: str = "ajt__pitch_accent_lookup"
    _css_relpath = f"{anki_addon_web_relpath()}/ajt_webview.css"
    _pronunciations: AccentDict
    _web: Optional[AnkiWebView]

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._web = AnkiWebView(parent=self, title=ACTION_NAME)
        self._web.setProperty("url", QUrl("about:blank"))
        self._web.setObjectName(self._name)
        self._pronunciations = OrderedDict()
        self._setup_ui()
        tweak_window(self)

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle(f"{ADDON_NAME} - {ACTION_NAME}")
        self.setMinimumSize(420, 240)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._web)
        layout.addLayout(self._make_bottom_buttons())

    def _make_bottom_buttons(self) -> QLayout:
        buttons = (
            ("Ok", self.accept),
            ("Copy HTML to Clipboard", self._copy_pronunciations),
        )
        hbox = QHBoxLayout()
        for label, action in buttons:
            button = QPushButton(label)
            qconnect(button.clicked, action)
            hbox.addWidget(button)
        hbox.addStretch()
        return hbox

    def _copy_pronunciations(self) -> None:
        if clip := QApplication.clipboard():
            return clip.setText(
                format_pronunciations(
                    self._pronunciations,
                    sep_single="、",
                    sep_multi="<br>",
                    expr_sep="：",
                    max_results=99,
                )
            )
        tooltip("couldn't get clipboard.", parent=self)

    def lookup_pronunciations(self, search: str):
        with Sqlite3Buddy() as db:
            self._pronunciations.update(lookup.with_new_buddy(db).get_pronunciations(search, group_by_headword=True))
        return self

    def _format_html_result(self) -> str:
        """Create HTML body"""
        html = io.StringIO()
        html.write('<main class="ajt__pitch_lookup">')
        for word, entries in self._pronunciations.items():
            html.write(f'<div class="keyword">{to_hiragana(word)}</div>')
            html.write('<div class="pitch_accents">')
            html.write("<ul>")
            for entry in entries_to_html(entries):
                html.write(f"<li>{entry}</li>")
            html.write("</ul>")
            html.write(f"</div>")
        html.write("</main>")
        return html.getvalue()

    def set_html_result(self):
        """Format pronunciations as an HTML list."""
        self._web.stdHtml(
            body=self._format_html_result(),
            css=[self._css_relpath],
        )
        return self

    def done(self, *args, **kwargs) -> None:
        self.on_close()
        return super().done(*args, **kwargs)

    def on_close(self) -> None:
        print("closing AJT lookup window...")
        self._web = None
        self._pronunciations.clear()


def on_lookup_pronunciation(parent: QWidget, text: str) -> None:
    """Do a lookup on the selection"""
    if text := clean_furigana(text).strip():
        ViewPitchAccentsDialog(parent).lookup_pronunciations(text).set_html_result().show()
    else:
        tooltip(_("Empty selection."), parent=((parent.window() or mw) if isinstance(parent, AnkiWebView) else parent))


def setup_mw_lookup_action(root_menu: QMenu) -> None:
    """Add a main window entry"""
    assert mw
    action = QAction(ACTION_NAME, root_menu)
    qconnect(action.triggered, lambda: on_lookup_pronunciation(mw, mw.web.selectedText()))
    if shortcut := cfg.pitch_accent.lookup_shortcut:
        action.setShortcut(shortcut)
    root_menu.addAction(action)


def add_context_menu_item(webview: AnkiWebView, menu: QMenu) -> None:
    """Add a context menu entry"""
    menu.addAction(ACTION_NAME, lambda: on_lookup_pronunciation(webview, webview.selectedText()))


def setup_browser_menu(browser: Browser) -> None:
    """Add a browser entry"""
    action = QAction(ACTION_NAME, browser)
    qconnect(
        action.triggered,
        lambda: on_lookup_pronunciation(browser, browser.editor.web.selectedText() if browser.editor else ""),
    )
    if shortcut := cfg.pitch_accent.lookup_shortcut:
        action.setShortcut(shortcut)
    # This is the "Go" menu.
    browser.form.menuJump.addAction(action)


def init() -> None:
    # Create the manual look-up menu entry
    setup_mw_lookup_action(menu_root_entry())
    # Hook to context menu events
    gui_hooks.editor_will_show_context_menu.append(add_context_menu_item)
    gui_hooks.webview_will_show_context_menu.append(add_context_menu_item)
    # Hook to the browser in order to have the keyboard shortcut work there as well.
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
