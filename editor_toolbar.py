# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from typing import Callable, NamedTuple, Iterable

from anki.notes import Note
from aqt import gui_hooks
from aqt.editor import Editor

from .config_view import config_view as cfg, ToolbarButtonConfig
from .helpers.profiles import TaskCaller
from .helpers.tokens import clean_furigana
from .reading import generate_furigana
from .tasks import DoTasks


class ToolbarButton(NamedTuple):
    id: str
    on_press: Callable[[Editor], None]
    tip: str
    conf: ToolbarButtonConfig


def modify_field(func: Callable[[str], str]) -> Callable[[Editor], None]:
    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        if (note := editor.note) and (field_n := editor.currentField) is not None:
            note.fields[field_n] = func(note.fields[field_n])
            editor.loadNoteKeepingFocus()

    return decorator


def modify_note(func: Callable[[Note], object]) -> Callable[[Editor], None]:
    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        if note := editor.note:
            func(note)
            if editor.currentField is None:
                editor.loadNote(focusTo=0)
            else:
                editor.loadNoteKeepingFocus()

    return decorator


def query_buttons() -> Iterable[ToolbarButton]:
    return (
        ToolbarButton(
            id='generate_all_button',
            on_press=modify_note(lambda note: DoTasks(note, caller=TaskCaller.toolbar_button, overwrite=False).run()),
            tip='Generate all fields',
            conf=cfg.toolbar.generate_all_button
        ),
        ToolbarButton(
            id='regenerate_all_button',
            on_press=modify_note(lambda note: DoTasks(note, caller=TaskCaller.toolbar_button, overwrite=True).run()),
            tip='Regenerate all fields (overwrite existing data)',
            conf=cfg.toolbar.regenerate_all_button
        ),
        ToolbarButton(
            id='furigana_button',
            on_press=modify_field(generate_furigana),
            tip='Generate furigana in the field',
            conf=cfg.toolbar.furigana_button
        ),
        ToolbarButton(
            id='hiragana_button',
            on_press=modify_field(functools.partial(generate_furigana, full_hiragana=True)),
            tip='Reconvert the field as hiragana',
            conf=cfg.toolbar.hiragana_button
        ),
        ToolbarButton(
            id='clean_furigana_button',
            on_press=modify_field(clean_furigana),
            tip='Clean furigana in the field',
            conf=cfg.toolbar.clean_furigana_button
        ),
    )


def add_toolbar_buttons(html_buttons: list[str], editor: Editor) -> None:
    html_buttons.extend(
        editor.addButton(
            icon=None,
            cmd=f'ajt__{b.id}',
            func=b.on_press,
            tip=f"{b.tip} ({b.conf.shortcut})" if b.conf.shortcut else b.tip,
            keys=b.conf.shortcut or None,
            label=b.conf.text,
        )
        for b in query_buttons() if b.conf.enabled
    )


def init():
    gui_hooks.editor_did_init_buttons.append(add_toolbar_buttons)
