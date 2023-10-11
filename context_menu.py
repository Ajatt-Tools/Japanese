# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import subprocess
from distutils.spawn import find_executable
from typing import Optional

from aqt import gui_hooks
from aqt.editor import EditorWebView, Editor
from aqt.qt import *
from aqt.utils import tooltip

from .config_view import config_view as cfg
from .mecab_controller.kana_conv import to_katakana, to_hiragana
from .mecab_controller.unify_readings import literal_pronunciation
from .reading import generate_furigana


class ContextMenuAction(abc.ABC):
    subclasses: list[type['ContextMenuAction']] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)

    def __init__(self, editor: Editor):
        self.editor = editor

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
    def action(self, text: str) -> str:
        pass

    def get_editor_selected_text(self) -> Optional[str]:
        if self.editor.currentField is not None and len(sel_text := self.editor.web.selectedText()) > 0:
            return sel_text

    def __call__(self, *args, **kwargs) -> None:
        if sel_text := self.get_editor_selected_text():
            self.editor.doPaste(self.action(sel_text), internal=True, extended=False)
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
    label = "Look up in GoldenDict"
    goldendict_exe = find_executable("goldendict")

    def action(self, text: str) -> None:
        """
        Call GoldenDict and pass it the selected text.
        """
        if self.goldendict_exe is None:
            tooltip("GoldenDict is not installed. Doing nothing.")
        else:
            subprocess.Popen(
                (self.goldendict_exe, text),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

    def __call__(self, *args, **kwargs) -> None:
        if sel_text := self.get_editor_selected_text():
            self.action(sel_text)
        else:
            tooltip("No text selected.")


def add_context_menu_items(webview: EditorWebView, menu: QMenu) -> None:
    for Action in ContextMenuAction.subclasses:
        if Action.enabled():
            action = menu.addAction(str(Action.label))
            qconnect(action.triggered, Action(webview.editor))


def init():
    gui_hooks.editor_will_show_context_menu.append(add_context_menu_items)
