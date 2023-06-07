# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from typing import Callable, NamedTuple, Iterable

from anki.notes import Note
from aqt import gui_hooks
from aqt.editor import Editor

from .audio import aud_src_mgr, format_audio_tags
from .config_view import config_view as cfg, ToolbarButtonConfig
from .helpers.profiles import TaskCaller
from .helpers.tokens import clean_furigana
from .reading import generate_furigana
from .tasks import DoTasks
from .widgets.anki_style import fix_default_anki_style
from .widgets.audio_search import AnkiAudioSearchDialog


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


def modify_note(func: Callable[[Editor], object]) -> Callable[[Editor], None]:
    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        if editor.note:
            # Note must be set to proceed.
            func(editor)
            if editor.currentField is None:
                editor.loadNote(focusTo=0)
            else:
                editor.loadNoteKeepingFocus()

    return decorator


def search_audio(editor: Editor):
    dialog = AnkiAudioSearchDialog(aud_src_mgr)
    fix_default_anki_style(dialog.table)
    dialog.set_note_fields(editor.note.keys(), selected_field_name=cfg.audio_settings.search_dialog_field_name)
    dialog.search(editor.web.selectedText())
    if not dialog.exec():
        return
    results = dialog.files_to_add()
    cfg.audio_settings.search_dialog_field_name = dialog.destination_field_name()
    editor.note[dialog.destination_field_name()] += format_audio_tags(results)
    aud_src_mgr.download_tags_bg(results)
    cfg.write_config()


def query_buttons() -> Iterable[ToolbarButton]:
    return (
        ToolbarButton(
            id='generate_all_button',
            on_press=modify_note(lambda editor: DoTasks(
                editor.note,
                caller=TaskCaller.toolbar_button,
                overwrite=False,
            ).run()),
            tip='Generate all fields',
            conf=cfg.toolbar.generate_all_button
        ),
        ToolbarButton(
            id='regenerate_all_button',
            on_press=modify_note(lambda editor: DoTasks(
                editor.note,
                caller=TaskCaller.toolbar_button,
                overwrite=True,
            ).run()),
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
        ToolbarButton(
            id='audio_search_button',
            on_press=modify_note(search_audio),
            tip='Search audio files to add to note',
            conf=cfg.toolbar.audio_search_button
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
