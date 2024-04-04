# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections import OrderedDict
from gettext import gettext as _

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import showInfo, restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from .ajt_common.about_menu import menu_root_entry, tweak_window
from .config_view import config_view as cfg
from .helpers.tokens import clean_furigana
from .reading import get_pronunciations, format_pronunciations, update_html

ACTION_NAME = "Pitch Accent lookup"


class ViewPitchAccentsDialog(QDialog):
    assert mw, "Anki must be initialized."

    _web_relpath = f"/_addons/{mw.addonManager.addonFromModule(__name__)}/web"
    _css_relpath = f"{_web_relpath}/pitch_lookup.css"

    mw.addonManager.setWebExports(__name__, r"(img|web)/.*\.(js|css|html|png|svg)")

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._webview = AnkiWebView(parent=self, title=ACTION_NAME)
        self._pronunciations = None
        self._setup_ui()

    def _setup_ui(self):
        tweak_window(self)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(ACTION_NAME)
        self.setMinimumSize(420, 240)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._webview)
        layout.addLayout(self._make_bottom_buttons())
        restoreGeom(self, ACTION_NAME)

    def _make_bottom_buttons(self):
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

    def _copy_pronunciations(self):
        return QApplication.clipboard().setText(
            format_pronunciations(
                self._pronunciations,
                sep_single="、",
                sep_multi="<br>",
                expr_sep="：",
                max_results=99,
            )
        )

    def lookup_pronunciations(self, search: str):
        self._pronunciations = get_pronunciations(search)
        return self

    def set_html_result(self):
        """Format pronunciations as an HTML list."""
        ordered_dict = OrderedDict()
        for word, entries in self._pronunciations.items():
            ordered_dict[word] = "".join(
                dict.fromkeys(f"<li>{update_html(entry.html_notation)}[{entry.pitch_number}]</li>" for entry in entries)
            )

        entries = []
        for word, html in ordered_dict.items():
            entries.append(f'<div class="keyword">{word}</div><div class="pitch_accents"><ol>{html}</ol></div>')

        self._webview.stdHtml(
            body=f'<main class="pitch_lookup">{"".join(entries)}</main>',
            css=[self._css_relpath],
        )
        return self

    def reject(self) -> None:
        self._webview = None
        return super().reject()

    def accept(self) -> None:
        self._webview = None
        return super().accept()

    def done(self, *args, **kwargs) -> None:
        saveGeom(self, ACTION_NAME)
        return super().done(*args, **kwargs)


def on_lookup_pronunciation(parent: QWidget, text: str):
    """Do a lookup on the selection"""
    if text := clean_furigana(text).strip():
        (ViewPitchAccentsDialog(parent).lookup_pronunciations(text).set_html_result().exec())
    else:
        showInfo(_("Empty selection."))


def setup_mw_lookup_action(root_menu: QMenu) -> None:
    """Add a main window entry"""
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
    qconnect(action.triggered, lambda: on_lookup_pronunciation(browser, browser.editor.web.selectedText()))
    if shortcut := cfg.pitch_accent.lookup_shortcut:
        action.setShortcut(shortcut)
    # This is the "Go" menu.
    browser.form.menuJump.addAction(action)


def init():
    # Create the manual look-up menu entry
    setup_mw_lookup_action(menu_root_entry())
    # Hook to context menu events
    gui_hooks.editor_will_show_context_menu.append(add_context_menu_item)
    gui_hooks.webview_will_show_context_menu.append(add_context_menu_item)
    # Hook to the browser in order to have the keyboard shortcut work there as well.
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
