# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from collections.abc import Callable, Iterable
from typing import NamedTuple

import anki.collection
from anki.collection import OpChanges
from anki.notes import Note
from aqt import gui_hooks, mw
from aqt.editor import Editor
from aqt.operations import CollectionOp

from .ajt_common.consts import ADDON_SERIES
from .audio import aud_src_mgr
from .audio_manager.forvo_client import ForvoClient
from .config_view import JapaneseConfig, ToolbarButtonConfig, get_global_config
from .database.sqlite3_buddy import Sqlite3Buddy
from .furigana.gen_furigana import FuriganaGen, get_global_furigana_generator
from .helpers.profiles import TaskCaller
from .helpers.tokens import clean_furigana
from .tasks import DoTasks
from .widgets.anki_style import fix_default_anki_style
from .widgets.audio_search import AnkiAudioSearchDialog


class ToolbarButton(NamedTuple):
    """Describes a single editor toolbar button: its action, tooltip, and config."""

    id: str
    on_press: Callable[[Editor], None]
    tip: str
    conf: ToolbarButtonConfig


def carefully_update_note(col: anki.collection.Collection, note: Note) -> OpChanges:
    """Update a note in the collection, skipping if the note has not been saved yet (Add window)."""
    if note.id > 0:
        # Anki can't update notes in the "Add" window.
        # It can only update notes in the "Browser" and "Edit" windows.
        return col.update_note(note)
    return OpChanges()


def modify_field(func: Callable[[str], str]) -> Callable[[Editor], None]:
    """Decorator that applies a string-transforming function to the current editor field.

    The wrapped function receives the current field's text and returns the modified text.
    The update is performed as a single undoable CollectionOp.
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
    """Decorator that runs a note-modifying function and persists the result.

    The wrapped function receives the Editor and may mutate editor.note in place.
    After it returns, the note is saved via a CollectionOp and the editor is reloaded.
    """

    def note_reload(editor: Editor) -> None:
        if editor.currentField is None:
            editor.loadNote(focusTo=0)
        else:
            editor.loadNoteKeepingFocus()

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


def get_note_value(note: Note, field_name: str) -> str | None:
    """
    Try to access field with name field_name.
    Suppress KeyError and return None if the field with this name doesn't exist.
    """
    try:
        return note[field_name]
    except KeyError:
        return None


class EditorMenus:
    """Manages AJT Japanese toolbar buttons in the Anki editor."""

    _cfg: JapaneseConfig

    def __init__(self, cfg: JapaneseConfig, fgen: FuriganaGen) -> None:
        self._cfg = cfg
        self._fgen = fgen

    def _search_audio(self, editor: Editor) -> None:
        """Open the audio search dialog, insert selected audio tags, and trigger download."""
        # the caller should have ensured that editor.note is not None.

        assert editor.note, "Note must be present."

        with Sqlite3Buddy() as db:
            session = aud_src_mgr.request_new_session(db)
            forvo_client = ForvoClient(config=self._cfg.forvo) if self._cfg.forvo.enable_forvo_search else None
            dialog = AnkiAudioSearchDialog(session, forvo_client)
            fix_default_anki_style(dialog.table)
            dialog.set_note_fields(
                editor.note.keys(),
                selected_src_field_name=self._cfg.audio_settings.search_dialog_src_field_name,
                selected_dest_field_name=self._cfg.audio_settings.search_dialog_dest_field_name,
            )
            dialog.search(
                editor.web.selectedText()
                or get_note_value(note=editor.note, field_name=self._cfg.audio_settings.search_dialog_src_field_name)
            )
            # Show the dialog.
            is_accepted = dialog.exec()

            # remember field names for later calls
            self._cfg.audio_settings.search_dialog_src_field_name = dialog.source_field_name
            self._cfg.audio_settings.search_dialog_dest_field_name = dialog.destination_field_name
            self._cfg.write_config()

            if not is_accepted:
                # The user pressed "Cancel". Nothing to do.
                return

            # process results
            results = dialog.files_to_add()
            if not results:
                return

            # Pre-reserve filenames so that [sound:...] tags use the actual (normalized) names.
            audio_tags, reserved = session.reserve_and_format_tags(results)
            editor.note[dialog.destination_field_name] = (
                editor.note[dialog.destination_field_name]
                + (self._cfg.audio_settings.tag_separator if editor.note[dialog.destination_field_name] else "")
                + audio_tags
            )
            session.download_reserved(reserved)

    def _query_buttons(self) -> Iterable[ToolbarButton]:
        """Yield all configured toolbar buttons with their actions and tooltips."""
        return (
            ToolbarButton(
                id="generate_all_button",
                on_press=modify_note(
                    lambda editor: editor.note
                    and DoTasks(
                        editor.note,
                        cfg=self._cfg,
                        caller=TaskCaller.toolbar_button,
                        overwrite=False,
                    ).run()
                ),
                tip="Generate all fields",
                conf=self._cfg.toolbar.generate_all_button,
            ),
            ToolbarButton(
                id="regenerate_all_button",
                on_press=modify_note(
                    lambda editor: editor.note
                    and DoTasks(
                        editor.note,
                        cfg=self._cfg,
                        caller=TaskCaller.toolbar_button,
                        overwrite=True,
                    ).run()
                ),
                tip="Regenerate all fields (overwrite existing data)",
                conf=self._cfg.toolbar.regenerate_all_button,
            ),
            ToolbarButton(
                id="furigana_button",
                on_press=modify_field(self._generate_furigana),
                tip="Generate furigana in the field",
                conf=self._cfg.toolbar.furigana_button,
            ),
            ToolbarButton(
                id="hiragana_button",
                on_press=modify_field(functools.partial(self._generate_furigana, full_hiragana=True)),
                tip="Reconvert the field as hiragana",
                conf=self._cfg.toolbar.hiragana_button,
            ),
            ToolbarButton(
                id="clean_furigana_button",
                on_press=modify_field(clean_furigana),
                tip="Clean furigana in the field",
                conf=self._cfg.toolbar.clean_furigana_button,
            ),
            ToolbarButton(
                id="audio_search_button",
                on_press=modify_note(self._search_audio),
                tip="Search audio files to add to note",
                conf=self._cfg.toolbar.audio_search_button,
            ),
        )

    def _generate_furigana(self, src_text: str, full_hiragana: bool = False) -> str:
        """Generate furigana for the source text using a temporary db connection."""
        with Sqlite3Buddy() as db:
            return self._fgen.with_new_buddy(db).generate_furigana(
                src_text,
                full_hiragana=full_hiragana,
            )

    def add_toolbar_buttons(self, html_buttons: list[str], editor: Editor) -> None:
        """Register enabled toolbar buttons with the Anki editor."""
        html_buttons.extend(
            editor.addButton(
                icon=None,
                cmd=f"{ADDON_SERIES}__{b.id}".lower(),
                func=b.on_press,
                tip=f"{b.tip} ({b.conf.shortcut})" if b.conf.shortcut else b.tip,
                keys=b.conf.shortcut or None,
                label=b.conf.text,
            )
            for b in self._query_buttons()
            if b.conf.enabled
        )


def init() -> None:
    """Create the EditorMenus instance and register it with Anki's editor hook."""
    assert mw, "Anki should be open."
    mw._ajt__japanese_editor_menus = menus = EditorMenus(
        cfg=get_global_config(),
        fgen=get_global_furigana_generator(),
    )
    gui_hooks.editor_did_init_buttons.append(menus.add_toolbar_buttons)
