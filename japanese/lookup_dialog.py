# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import io
import pathlib
from collections.abc import Collection
from gettext import gettext as _
from typing import final

import aqt
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from .ajt_common.about_menu import disable_help_button, menu_root_entry
from .config_view import (
    JapaneseConfig,
    LookupDialogPitchOutputFormat,
    get_global_config,
)
from .database.sqlite3_buddy import Sqlite3Buddy
from .helpers.consts import ADDON_NAME
from .helpers.tokens import clean_furigana
from .helpers.webview_utils import (
    AJT_WEBVIEW_CSS_FILE_NAME,
)
from .pitch_accents.accent_lookup import AccentLookup, get_global_accent_lookup
from .pitch_accents.common import AccentDict, FormattedEntry
from .pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from .pitch_accents.format_entries import EntryFormatter
from .pitch_accents.styles import HTMLPitchPatternStyle
from .widgets.raise_on_show_dialog import RaiseOnShowDialog
from .widgets.webview import SVGPreviewWebView, get_svg_preview_webview

ACTION_NAME = "Pitch Accent lookup"


def get_parent_widget(parent: QWidget | None) -> QWidget | None:
    """Return a concrete parent widget suitable for dialogs and tooltips."""
    if parent is None:
        return mw
    elif isinstance(parent, AnkiWebView):
        return parent.window() or mw
    else:
        return parent


@final
class ViewPitchAccentsDialog(RaiseOnShowDialog):
    """Dialog that displays pitch accent lookup results.

    The dialog is persistent: it is created once and reused for every lookup.
    """

    name: str = "ajt__pitch_accent_lookup"
    _pronunciations: AccentDict
    _web: SVGPreviewWebView
    _cfg: JapaneseConfig
    _accent_lookup: AccentLookup
    _formatter: EntryFormatter
    _svg_maker: FormattedEntryToSvgAdapter
    _accent_db_path: pathlib.Path | None

    def __init__(
        self,
        cfg: JapaneseConfig,
        parent: QWidget | None = None,
        accent_lookup: AccentLookup | None = None,
        accent_db_path: pathlib.Path | None = None,
    ) -> None:
        """Initialize the lookup result dialog with add-on config and optional dependencies.

        When Anki is running, the cached global AccentLookup instance is used.
        Standalone runs (tests, playground) must pass their own AccentLookup
        and a path to the database file.
        """
        super().__init__(parent)
        self._cfg = cfg
        self._accent_lookup = accent_lookup or get_global_accent_lookup()
        self._accent_db_path = accent_db_path
        self._svg_maker = FormattedEntryToSvgAdapter(cfg)
        self._formatter = EntryFormatter(cfg, svg_maker=self._svg_maker)
        self._web = get_svg_preview_webview(
            self,
            action_name=ACTION_NAME,
            css_file_names=(AJT_WEBVIEW_CSS_FILE_NAME,),
        )
        self._web.setProperty("url", QUrl("about:blank"))
        self._web.setObjectName(self.name)
        self._pronunciations = {}
        self._setup_ui()
        disable_help_button(self)

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
            ("Ok", lambda: self.accept()),
            ("Copy HTML to Clipboard", lambda: self._copy_pronunciations()),
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
                self._formatter.format_pronunciations(
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
        match style := self._cfg.pitch_accent.html_style:
            case HTMLPitchPatternStyle.none:
                # 'none' can't be selected here because it is intended for anki card customization.
                return HTMLPitchPatternStyle.u_biq_color_coded
            case _:
                return style

    def _get_notation(self, entry: FormattedEntry, mode: LookupDialogPitchOutputFormat) -> str:
        """Format one pronunciation entry in the requested notation mode."""
        match mode:
            case LookupDialogPitchOutputFormat.html:
                return (
                    f'<span class="pitch_html">{self._formatter.update_html(entry, self._html_style())}</span>'
                    f" {entry.pitch_number_html}"
                )
            case LookupDialogPitchOutputFormat.svg:
                return f"{self._svg_maker.make_graph(entry)} {entry.pitch_number_html}"
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
        self._web.set_formatted_html(self._format_html_result(), self._cfg.svg_graphs.color_mode)

    def done(self, result: int) -> None:
        """Close the dialog and let Qt finalize the dialog result."""
        # https://doc.qt.io/qt-6/qdialog.html#done
        print("closing AJT lookup window...")
        super().done(result)

    def lookup_pronunciations(self, text: str, parent: QWidget | None = None) -> None:
        """Do a lookup on the selected text, showing results or an empty-selection tooltip.

        The parent widget is used to position the tooltip near the window the
        lookup was triggered from (e.g. the Browser instead of the main window).
        """
        if text := clean_furigana(text).strip():
            with Sqlite3Buddy(self._accent_db_path) as db:
                self._pronunciations = self._accent_lookup.with_new_buddy(db).get_pronunciations(
                    text, group_by_headword=True
                )
            self._set_html_result()
            self.show()
        else:
            tooltip(msg=_("Empty selection."), parent=get_parent_widget(parent or self.parent()))


class LookupMenus:
    """Installer for lookup actions in Anki menus and context menus."""

    def __init__(self, cfg: JapaneseConfig, parent: aqt.AnkiQt | None = None) -> None:
        """Store config for dialog callbacks."""
        self._cfg = cfg
        self._mw = parent
        self._dialog = ViewPitchAccentsDialog(self._cfg, parent=self._mw)

    def setup_mw_lookup_action(self, root_menu: QMenu) -> None:
        """Add a main window entry"""
        assert mw, "Anki must be running."
        action = QAction(f"🔍 {ACTION_NAME}", root_menu)
        qconnect(action.triggered, lambda: self._dialog.lookup_pronunciations(mw.web.selectedText(), parent=mw))
        if shortcut := self._cfg.pitch_accent.lookup_shortcut:
            action.setShortcut(shortcut)
        root_menu.addAction(action)

    def add_context_menu_item(self, webview: AnkiWebView, menu: QMenu) -> None:
        """Add a context menu entry"""
        menu.addAction(ACTION_NAME, lambda: self._dialog.lookup_pronunciations(webview.selectedText(), parent=webview))

    def setup_browser_menu(self, browser: Browser) -> None:
        """Add a browser entry"""
        action = QAction(ACTION_NAME, browser)
        qconnect(
            action.triggered,
            lambda: self._dialog.lookup_pronunciations(
                browser.editor.web.selectedText() if browser.editor else "", parent=browser
            ),
        )
        if shortcut := self._cfg.pitch_accent.lookup_shortcut:
            action.setShortcut(shortcut)
        # This is the "Go" menu.
        browser.form.menuJump.addAction(action)


def init() -> None:
    """Initialize lookup menu entries and context menu hooks."""
    cfg = get_global_config()
    menus = LookupMenus(cfg, mw)
    # Create the manual look-up menu entry
    menus.setup_mw_lookup_action(menu_root_entry())
    # Hook to context menu events
    gui_hooks.editor_will_show_context_menu.append(menus.add_context_menu_item)
    gui_hooks.webview_will_show_context_menu.append(menus.add_context_menu_item)
    # Hook to the browser in order to have the keyboard shortcut work there as well.
    gui_hooks.browser_menus_did_init.append(menus.setup_browser_menu)
