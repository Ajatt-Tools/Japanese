# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from collections.abc import Iterable
from typing import Callable, NamedTuple, Optional

import anki.collection
from anki.collection import OpChanges
from anki.notes import Note
from aqt import gui_hooks
from aqt.editor import Editor
from aqt.operations import CollectionOp

from .ajt_common.consts import ADDON_SERIES
from .audio import aud_src_mgr, format_audio_tags
from .audio_manager.forvo_client import ForvoClient
from .config_view import ToolbarButtonConfig
from .config_view import config_view as cfg
from .database.sqlite3_buddy import Sqlite3Buddy
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


def carefully_update_note(col: anki.collection.Collection, note: Note) -> OpChanges:
    if note.id > 0:
        # Anki can't update notes in the "Add" window.
        # It can only update notes in the "Browser" and "Edit" windows.
        return col.update_note(note)
    return OpChanges()


def modify_field(func: Callable[[str], str]) -> Callable[[Editor], None]:
    """
    Used to generate or clean furigana in the current field.
    """

    def collection_op(col: anki.collection.Collection, note: Note, field_n: int) -> OpChanges:
        pos = col.add_custom_undo_entry(f"{ADDON_SERIES}: Modify field {note.keys()[field_n]}.")
        note.fields[field_n] = func(note.fields[field_n])
        carefully_update_note(col, note)
        return col.merge_undo_entries(pos)

    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        if (note := editor.note) and (field_n := editor.currentField) is not None:
            CollectionOp(
                parent=editor.widget,
                op=lambda col: collection_op(col, note, field_n),
            ).success(
                lambda out: editor.loadNoteKeepingFocus(),
            ).run_in_background()

    return decorator


def modify_note(func: Callable[[Editor], object]) -> Callable[[Editor], None]:
    """
    Used to (re)generate all target fields of the current note.
    """

    def note_reload(editor: Editor):
        return editor.loadNote(focusTo=0) if editor.currentField is None else editor.loadNoteKeepingFocus()

    @functools.wraps(func)
    def decorator(editor: Editor) -> None:
        # Note must be set to proceed.
        if editor.note:
            func(editor)
            CollectionOp(
                parent=editor.widget,
                op=lambda col: carefully_update_note(col, editor.note),
            ).success(
                lambda out: note_reload(editor),
            ).run_in_background()

    return decorator


def get_note_value(note: Note, field_name: str) -> Optional[str]:
    """
    Try to access field with name field_name.
    Suppress KeyError and return None if the field with this name doesn't exist.
    """
    try:
        return note[field_name]
    except KeyError:
        return None


def search_audio(editor: Editor) -> None:
    # the caller should have ensured that editor.note is not None.

    assert editor.note is not None

    with Sqlite3Buddy() as db:
        session = aud_src_mgr.request_new_session(db)
        forvo_client = ForvoClient(config=cfg.forvo) if cfg.forvo.enable_forvo_search else None
        dialog = AnkiAudioSearchDialog(session, forvo_client)
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
        # Show the dialog.
        is_accepted = dialog.exec()

        # remember field names for later calls
        cfg.audio_settings.search_dialog_src_field_name = dialog.source_field_name
        cfg.audio_settings.search_dialog_dest_field_name = dialog.destination_field_name
        cfg.write_config()

        if not is_accepted:
            # The user pressed "Cancel". Nothing to do.
            return

        # process results
        results = dialog.files_to_add()
        if not results:
            return

        editor.note[dialog.destination_field_name] = (
            editor.note[dialog.destination_field_name]
            + (cfg.audio_settings.tag_separator if editor.note[dialog.destination_field_name] else "")
            + format_audio_tags(results)
        )
        session.download_and_save_tags(results)


def query_buttons() -> Iterable[ToolbarButton]:
    return (
        ToolbarButton(
            id="generate_all_button",
            on_press=modify_note(
                lambda editor: DoTasks(
                    editor.note,
                    caller=TaskCaller.toolbar_button,
                    overwrite=False,
                ).run()
            ),
            tip="Generate all fields",
            conf=cfg.toolbar.generate_all_button,
        ),
        ToolbarButton(
            id="regenerate_all_button",
            on_press=modify_note(
                lambda editor: DoTasks(
                    editor.note,
                    caller=TaskCaller.toolbar_button,
                    overwrite=True,
                ).run()
            ),
            tip="Regenerate all fields (overwrite existing data)",
            conf=cfg.toolbar.regenerate_all_button,
        ),
        ToolbarButton(
            id="furigana_button",
            on_press=modify_field(generate_furigana),
            tip="Generate furigana in the field",
            conf=cfg.toolbar.furigana_button,
        ),
        ToolbarButton(
            id="hiragana_button",
            on_press=modify_field(functools.partial(generate_furigana, full_hiragana=True)),
            tip="Reconvert the field as hiragana",
            conf=cfg.toolbar.hiragana_button,
        ),
        ToolbarButton(
            id="clean_furigana_button",
            on_press=modify_field(clean_furigana),
            tip="Clean furigana in the field",
            conf=cfg.toolbar.clean_furigana_button,
        ),
        ToolbarButton(
            id="audio_search_button",
            on_press=modify_note(search_audio),
            tip="Search audio files to add to note",
            conf=cfg.toolbar.audio_search_button,
        ),
    )


def add_toolbar_buttons(html_buttons: list[str], editor: Editor) -> None:
    html_buttons.extend(
        editor.addButton(
            icon=None,
            cmd=f"ajt__{b.id}",
            func=b.on_press,
            tip=f"{b.tip} ({b.conf.shortcut})" if b.conf.shortcut else b.tip,
            keys=b.conf.shortcut or None,
            label=b.conf.text,
        )
        for b in query_buttons()
        if b.conf.enabled
    )


def init():
    gui_hooks.editor_did_init_buttons.append(add_toolbar_buttons)
