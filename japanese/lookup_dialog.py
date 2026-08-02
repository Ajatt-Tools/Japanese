# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import io
from collections.abc import Collection
from gettext import gettext as _
from typing import final

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from .ajt_common.about_menu import menu_root_entry, tweak_window
from .ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from .config_view import (
    JapaneseConfig,
    LookupDialogPitchOutputFormat,
    get_global_config,
)
from .database.sqlite3_buddy import Sqlite3Buddy
from .helpers.consts import ADDON_NAME
from .helpers.tokens import clean_furigana
from .pitch_accents.common import AccentDict, FormattedEntry
from .pitch_accents.styles import HTMLPitchPatternStyle
from .pitch_artist.pitch_accents_web_view import get_css_file_refs
from .reading import format_pronunciations, lookup, svg_graph_maker, update_html

ACTION_NAME = "Pitch Accent lookup"


def lookup_pronunciations(search: str) -> AccentDict:
    """Look up pitch accent pronunciations for the given search text."""
    with Sqlite3Buddy() as db:
        return lookup.with_new_buddy(db).get_pronunciations(search, group_by_headword=True)


def get_parent_widget(parent: QWidget | None) -> QWidget:
    """Return a concrete parent widget suitable for dialogs and tooltips."""
    if parent is None:
        return mw
    elif isinstance(parent, AnkiWebView):
        return parent.window() or mw
    else:
        return parent


@final
class ViewPitchAccentsDialog(AnkiSaveAndRestoreGeomDialog):
    """Dialog that displays pitch accent lookup results."""

    name: str = "ajt__pitch_accent_lookup"
    _pronunciations: AccentDict
    _web: AnkiWebView
    _cfg: JapaneseConfig

    def __init__(self, cfg: JapaneseConfig, pronunciations: AccentDict, parent: QWidget | None = None) -> None:
        """Initialize the lookup result dialog with pronunciations and add-on config."""
        super().__init__(parent)
        self._cfg = cfg
        self._web = AnkiWebView(parent=self, title=ACTION_NAME)
        self._web.setProperty("url", QUrl("about:blank"))
        self._web.setObjectName(self.name)
        self._pronunciations = pronunciations
        self._setup_ui()
        self._set_html_result()
        tweak_window(self)

    def _setup_ui(self) -> None:
        """Create the dialog layout and web view controls."""
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle(f"{ADDON_NAME} - {ACTION_NAME}")
        self.setMinimumSize(420, 240)
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._web)
        layout.addLayout(self._make_bottom_buttons())

    def _make_bottom_buttons(self) -> QLayout:
        """Create the bottom button row for closing and copying results."""
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
        """Copy the currently displayed pronunciations as HTML to the clipboard."""
        if clip := QApplication.clipboard():
            clip.setText(
                format_pronunciations(
                    self._pronunciations,
                    sep_single="、",
                    sep_multi="<br>",
                    expr_sep="：",
                    max_results=99,
                )
            )
            return
        tooltip("couldn't get clipboard.", parent=self)

    def _html_style(self) -> HTMLPitchPatternStyle:
        """Return the HTML style used for lookup pitch pattern rendering."""
        style = self._cfg.pitch_accent.html_style
        if style is HTMLPitchPatternStyle.none:
            # 'none' can't be selected here because it is intended for anki card customization.
            return HTMLPitchPatternStyle.u_biq_color_coded
        return style

    def _get_notation(self, entry: FormattedEntry, mode: LookupDialogPitchOutputFormat) -> str:
        """Format one pronunciation entry in the requested notation mode."""
        if mode == LookupDialogPitchOutputFormat.html:
            return (
                f'<span class="pitch_html">{update_html(entry, pitch_accent_style=self._html_style())}</span>'
                f" {entry.pitch_number_html}"
            )
        elif mode == LookupDialogPitchOutputFormat.svg:
            return f"{svg_graph_maker.make_graph(entry)} {entry.pitch_number_html}"
        raise RuntimeError("Unreachable.")

    def _entry_to_html(self, entry: FormattedEntry) -> str:
        """Convert one formatted entry to the configured lookup HTML notation."""
        return self._get_notation(entry, mode=self._cfg.pitch_accent.lookup_pitch_format)

    def _map_html_entry_to_headwords(self) -> dict[str, Collection[str]]:
        """Group equivalent rendered pitch entries by their matching headwords."""
        html_entry_to_headwords: dict[str, set[str]] = collections.defaultdict(set)
        for word, entries in self._pronunciations.items():
            for pitch_pattern in entries:
                html_entry_to_headwords[self._entry_to_html(pitch_pattern)].add(pitch_pattern.raw_headword)
        return html_entry_to_headwords

    def _format_html_result(self) -> str:
        """Create HTML body"""
        html = io.StringIO()
        html.write('<main class="ajt__pitch_lookup">')

        for pitch_pattern, headwords in self._map_html_entry_to_headwords().items():
            # Keyword (headword)
            html.write('<div class="keyword"><ul>')
            for headword in headwords:
                html.write(f"<li>{headword}</li>")
            html.write("</ul></div>")
            # Pitches (entries)
            html.write('<div class="pitch_accents">')
            html.write(pitch_pattern)
            html.write("</div>")
        html.write("</main>")
        return html.getvalue()

    def _set_html_result(self) -> None:
        """Format pronunciations as an HTML list."""
        self._web.stdHtml(
            body=self._format_html_result(),
            css=get_css_file_refs(self._cfg.svg_graphs.color_mode),
        )

    def done(self, result: int) -> None:
        """Close the dialog and let Qt finalize the dialog result."""
        # https://doc.qt.io/qt-6/qdialog.html#done
        print("closing AJT lookup window...")
        super().done(result)


class LookupMenus:
    """Installer for lookup actions in Anki menus and context menus."""

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Store config for dialog callbacks."""
        self._cfg = cfg

    def setup_mw_lookup_action(self, root_menu: QMenu) -> None:
        """Add a main window entry"""
        assert mw, "Anki must be running."
        action = QAction(f"🔍 {ACTION_NAME}", root_menu)
        qconnect(action.triggered, lambda: self._on_lookup_pronunciation(mw, mw.web.selectedText()))
        if shortcut := self._cfg.pitch_accent.lookup_shortcut:
            action.setShortcut(shortcut)
        root_menu.addAction(action)

    def add_context_menu_item(self, webview: AnkiWebView, menu: QMenu) -> None:
        """Add a context menu entry"""
        menu.addAction(ACTION_NAME, lambda: self._on_lookup_pronunciation(webview, webview.selectedText()))

    def setup_browser_menu(self, browser: Browser) -> None:
        """Add a browser entry"""
        action = QAction(ACTION_NAME, browser)
        qconnect(
            action.triggered,
            lambda: self._on_lookup_pronunciation(browser, browser.editor.web.selectedText() if browser.editor else ""),
        )
        if shortcut := self._cfg.pitch_accent.lookup_shortcut:
            action.setShortcut(shortcut)
        # This is the "Go" menu.
        browser.form.menuJump.addAction(action)

    def _on_lookup_pronunciation(self, parent: QWidget, text: str) -> None:
        """Do a lookup on the selection"""
        if text := clean_furigana(text).strip():
            ViewPitchAccentsDialog(cfg=self._cfg, pronunciations=lookup_pronunciations(text), parent=parent).show()
        else:
            tooltip(msg=_("Empty selection."), parent=get_parent_widget(parent))


def init() -> None:
    """Initialize lookup menu entries and context menu hooks."""
    cfg = get_global_config()
    menus = LookupMenus(cfg)
    # Create the manual look-up menu entry
    menus.setup_mw_lookup_action(menu_root_entry())
    # Hook to context menu events
    gui_hooks.editor_will_show_context_menu.append(menus.add_context_menu_item)
    gui_hooks.webview_will_show_context_menu.append(menus.add_context_menu_item)
    # Hook to the browser in order to have the keyboard shortcut work there as well.
    gui_hooks.browser_menus_did_init.append(menus.setup_browser_menu)
