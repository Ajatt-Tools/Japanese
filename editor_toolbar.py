# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from collections.abc import Iterable
from typing import Callable, NamedTuple, Optional

from anki.notes import Note
from aqt import gui_hooks
from aqt.editor import Editor

from .audio import aud_src_mgr, format_audio_tags
from .config_view import config_view as cfg, ToolbarButtonConfig
from .definitions import sakura_client
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
    def note_reload(editor: Editor):
        return (
            editor.loadNote(focusTo=0)
            if editor.currentField is None
            else editor.loadNoteKeepingFocus()
        )

    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        # Note must be set to proceed.
        if editor.note:
            func(editor)
            note_reload(editor)

    return decorator


def get_note_value(note: Note, field_name: str) -> Optional[str]:
    try:
        return note[field_name]
    except KeyError:
        return None


def search_audio(editor: Editor) -> None:
    # the caller should have ensured that editor.note is not None.
    with aud_src_mgr.request_new_session() as session:
        dialog = AnkiAudioSearchDialog(session)
        fix_default_anki_style(dialog.table)
        dialog.set_note_fields(
            editor.note.keys(),
            selected_src_field_name=cfg.audio_settings.search_dialog_src_field_name,
            selected_dest_field_name=cfg.audio_settings.search_dialog_dest_field_name,
        )
        dialog.search(
            editor.web.selectedText()
            or get_note_value(note=editor.note, field_name=cfg.audio_settings.search_dialog_src_field_name)
        )
        if not dialog.exec():
            return
        # remember field names for later calls
        cfg.audio_settings.search_dialog_src_field_name = dialog.source_field_name
        cfg.audio_settings.search_dialog_dest_field_name = dialog.destination_field_name
        cfg.write_config()
        # process results
        results = dialog.files_to_add()
        editor.note[dialog.destination_field_name] += format_audio_tags(results)
        session.download_and_save_tags(results)


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
        ToolbarButton(
            id='add_definition_button',
            on_press=modify_note(sakura_client.add_definition),
            tip='Add dictionary definition for the target word.',
            conf=cfg.toolbar.add_definition_button
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
