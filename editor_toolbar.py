# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from dataclasses import dataclass
from typing import List, Callable, Any, Collection

from anki.notes import Note
from aqt import gui_hooks
from aqt.editor import Editor

from .helpers.config import config, iter_tasks
from .helpers.tokens import clean_furigana
from .reading import generate_furigana, do_tasks


@dataclass(frozen=True)
class BtnCfg:
    id: str
    on_press: Callable[[Editor], None]
    tip: str

    @property
    def enabled(self) -> bool:
        return config['toolbar'][self.id]['enable']

    @property
    def shortcut(self) -> str:
        return config['toolbar'][self.id]['shortcut']

    @property
    def text(self) -> str:
        return config['toolbar'][self.id]['text']


def modify_field(func: Callable[[str], str]) -> Callable[[Editor], None]:
    def decorator(editor: Editor) -> None:
        if (note := editor.note) and (field_n := editor.currentField) is not None:
            note.fields[field_n] = func(note.fields[field_n])
            editor.loadNoteKeepingFocus()

    return decorator


def modify_note(func: Callable[[Note], Any]) -> Callable[[Editor], None]:
    def decorator(editor: Editor) -> None:
        if note := editor.note:
            func(note)
            editor.loadNoteKeepingFocus()

    return decorator


def create_callback(configs: Collection[BtnCfg]):
    def add_toolbar_buttons(buttons: List[str], editor: Editor) -> None:
        for cfg in configs:
            if cfg.enabled:
                b = editor.addButton(
                    icon=None,
                    cmd=cfg.id,
                    func=cfg.on_press,
                    tip=f"{cfg.tip} ({cfg.shortcut})",
                    keys=cfg.shortcut,
                    label=cfg.text,
                )
                buttons.append(b)

    return add_toolbar_buttons


def init():
    configs = (
        BtnCfg(
            id='furigana_button',
            on_press=modify_field(generate_furigana),
            tip='Generate furigana in the field',
        ),
        BtnCfg(
            id='generate_all_readings',
            on_press=modify_note(lambda note: do_tasks(note, iter_tasks(note))),
            tip='Fill all empty fields.',
        ),
        BtnCfg(
            id='clean_furigana_button',
            on_press=modify_field(clean_furigana),
            tip='Clean furigana in the field',
        ),
    )

    gui_hooks.editor_did_init_buttons.append(create_callback(configs))
