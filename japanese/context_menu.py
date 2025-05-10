# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import re
from typing import Optional

import aqt
from aqt import gui_hooks
from aqt.editor import Editor, EditorWebView
from aqt.qt import *
from aqt.utils import tooltip
from aqt.webview import AnkiWebView

from .config_view import config_view as cfg
from .helpers.goldendict_lookups import GD_PROGRAM_NAME, lookup_goldendict
from .helpers.half_kata import to_half_width_katakana
from .mecab_controller.kana_conv import to_hiragana, to_katakana
from .mecab_controller.unify_readings import literal_pronunciation
from .reading import generate_furigana


class ContextMenuAction(abc.ABC):
    subclasses: list[type["ContextMenuAction"]] = []
    shown_when_not_editing = False

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)

    def __init__(self, editor: Optional[Editor] = None, webview: Optional[AnkiWebView] = None) -> None:
        self.editor = editor
        self.webview = webview or editor.web

    def _parent_window(self) -> QWidget:
        if self.editor:
            return self.editor.parentWindow
        if self.webview:
            return self.webview.window() or aqt.mw
        raise RuntimeError("Parent should be passed to instance.")

    @classmethod
    def enabled(cls) -> bool:
        return cfg.context_menu.get(cls.key)

    @property
    @abc.abstractmethod
    def key(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def label(self) -> str:
        pass

    @abc.abstractmethod
    def action(self, text: str) -> Optional[str]:
        """
        When None is returned,
        it is a sign that nothing should be modified in the Editor's field.
        Otherwise, the returned text replaces the currently selected text.
        """
        pass

    def get_selected_text(self) -> Optional[str]:
        if self.editor is not None and self.editor.currentField is None:
            return None
        if len(sel_text := self.webview.selectedText()) > 0:
            return sel_text
        return None

    def __call__(self, *args, **kwargs) -> None:
        if sel_text := self.get_selected_text():
            if (result := self.action(sel_text)) is not None and self.editor is not None:
                self.editor.doPaste(result, internal=True, extended=False)
        else:
            tooltip("No text selected.")


class GenerateFurigana(ContextMenuAction):
    key = "generate_furigana"
    label = "Furigana for selection"
    action = staticmethod(generate_furigana)


class ToKatakana(ContextMenuAction):
    key = "to_katakana"
    label = "Convert to katakana"
    action = staticmethod(to_katakana)


class ToHalfWidthKatakana(ContextMenuAction):
    key = "to_half_width_katakana"
    label = "Convert to half-width katakana"
    action = staticmethod(to_half_width_katakana)


class ToHiragana(ContextMenuAction):
    key = "to_hiragana"
    label = "Convert to hiragana"
    action = staticmethod(to_hiragana)


class LiteralPronunciation(ContextMenuAction):
    key = "literal_pronunciation"
    label = "Literal pronunciation"
    action = staticmethod(literal_pronunciation)


class LookUpWord(ContextMenuAction):
    key = "look_up_word"
    label = f"Look up in {GD_PROGRAM_NAME}"
    shown_when_not_editing = True

    def action(self, text: str) -> None:
        """
        Call GoldenDict and pass it the selected text.
        """
        try:
            lookup_goldendict(text)
        except RuntimeError as ex:
            tooltip(str(ex), parent=self._parent_window())


class BrowserSearch(ContextMenuAction):
    key = "browser_search"
    label = "Browser Search"
    shown_when_not_editing = True

    def action(self, search_text: str) -> None:
        """
        Paste selected text into the Browser's search bar and perform search.
        """
        if not search_text:
            return tooltip("Empty selection.", parent=self._parent_window())
        browser = aqt.dialogs.open("Browser", aqt.mw)  # browser requires mw (AnkiQt) to be passed as parent
        browser.activateWindow()
        browser.search_for(search_text)


class RemoveSpaces(ContextMenuAction):
    key = "remove_spaces"
    label = "Remove all spaces"
    _re_space = re.compile(r"\s+", flags=re.MULTILINE | re.IGNORECASE)

    def action(self, text: str) -> str:
        """
        Remove all spaces from the text.
        """
        return re.sub(self._re_space, "", text)


def add_editor_context_menu_items(webview: EditorWebView, menu: QMenu) -> None:
    for Action in ContextMenuAction.subclasses:
        if Action.enabled():
            action: QAction = menu.addAction(str(Action.label))
            qconnect(action.triggered, Action(editor=webview.editor))


def add_webview_context_menu_items(webview: AnkiWebView, menu: QMenu) -> None:
    for Action in ContextMenuAction.subclasses:
        if Action.shown_when_not_editing and Action.enabled():
            action: QAction = menu.addAction(str(Action.label))
            qconnect(action.triggered, Action(webview=webview))


def init():
    gui_hooks.editor_will_show_context_menu.append(add_editor_context_menu_items)
    gui_hooks.webview_will_show_context_menu.append(add_webview_context_menu_items)
