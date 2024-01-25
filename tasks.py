# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
from typing import Optional, Callable, Any

import anki.collection
from anki import hooks
from anki.decks import DeckId
from anki.notes import Note
from anki.utils import strip_html_media
from aqt import mw

from .audio import format_audio_tags, AnkiAudioSourceManager
from .config_view import config_view as cfg
from .helpers import *
from .helpers.profiles import Profile, ProfileFurigana, PitchOutputFormat, ProfilePitch, ProfileAudio, TaskCaller
from .reading import format_pronunciations, get_pronunciations, generate_furigana


def note_type_matches(note_type: dict[str, Any], profile: Profile) -> bool:
    return profile.note_type.lower() in note_type['name'].lower()


def iter_tasks(note: Note, src_field: Optional[str] = None) -> Iterable[Profile]:
    note_type = note.note_type()
    for profile in cfg.iter_profiles():
        if note_type_matches(note_type, profile) and (src_field is None or profile.source == src_field):
            yield profile


def do_not_modify_destination_if_have_nothing_to_add(fn: Callable[['DoTask', str], str]):
    @functools.wraps(fn)
    def wrapper(self: 'DoTask', input_text: str, current_text: str):
        return (
            out
            if (out := fn(self, input_text)) and (out != input_text or not current_text)
            else current_text
        )

    return wrapper


class DoTask:
    _subclasses_map = {}  # e.g. ProfileFurigana -> AddFurigana
    _key_class_param = "task_type"

    def __init_subclass__(cls, **kwargs):
        task_type: type(Profile) = kwargs.pop(cls._key_class_param)  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[task_type] = cls

    def __new__(cls, task: Profile, *args, **kwargs):
        subclass = cls._subclasses_map[type(task)]
        return object.__new__(subclass)

    def __init__(self, task, caller: TaskCaller, aud_src_mgr: AnkiAudioSourceManager):
        self._task = task
        self._caller = caller
        self._aud_src_mgr = aud_src_mgr

    def run(self, *args, **kwargs) -> str:
        raise NotImplementedError()


class AddFurigana(DoTask, task_type=ProfileFurigana):
    @do_not_modify_destination_if_have_nothing_to_add
    def run(self, src_text: str) -> str:
        return generate_furigana(src_text, split_morphemes=self._task.split_morphemes)


class AddPitch(DoTask, task_type=ProfilePitch):
    @do_not_modify_destination_if_have_nothing_to_add
    def run(self, src_text: str) -> str:
        return format_pronunciations(
            pronunciations=get_pronunciations(src_text, use_mecab=self._task.split_morphemes),
            output_format=PitchOutputFormat[self._task.output_format],
            sep_single=cfg.pitch_accent.reading_separator,
            sep_multi=cfg.pitch_accent.word_separator,
        )


class AddAudio(DoTask, task_type=ProfileAudio):
    @do_not_modify_destination_if_have_nothing_to_add
    def run(self, src_text: str) -> str:
        search_results = self._aud_src_mgr.search_audio(
            src_text,
            split_morphemes=self._task.split_morphemes,
            ignore_inflections=cfg.audio_settings.ignore_inflections,
            stop_if_one_source_has_results=cfg.audio_settings.stop_if_one_source_has_results,
        )
        search_results = search_results[:cfg.audio_settings.maximum_results]
        self._aud_src_mgr.download_and_save_tags(
            search_results,
            run_in_background=(self._caller != TaskCaller.bulk_add),
        )
        return format_audio_tags(search_results)


def html_to_media_line(txt: str) -> str:
    """ Strip HTML but keep media filenames. """
    return strip_html_media(
        txt
        .replace("<br>", " ")
        .replace("<br />", " ")
        .replace("<div>", " ")
        .replace("\n", " ")
    ).strip()


class DoTasks:
    def __init__(
            self,
            note: Note,
            *,
            caller: TaskCaller,
            src_field: Optional[str] = None,
            overwrite: bool = False,
    ):
        self._note = note
        self._caller = caller
        self._tasks = iter_tasks(note, src_field)
        self._overwrite = overwrite

    def run(self, changed: bool = False) -> bool:
        from .audio import aud_src_mgr

        with aud_src_mgr.request_new_session() as aud_mgr:
            for task in self._tasks:
                if task.should_answer_to(self._caller):
                    changed = self._do_task(task, aud_mgr=aud_mgr) or changed
            return changed

    def _do_task(self, task: Profile, aud_mgr: AnkiAudioSourceManager) -> bool:
        changed = False
        if self._can_fill_destination(task) and (src_text := self._src_text(task)):
            self._note[task.destination] = DoTask(
                task, self._caller, aud_mgr,
            ).run(src_text, self._note[task.destination])
            changed = True
        return changed

    def _src_text(self, task: Profile) -> str:
        return mw.col.media.strip(self._note[task.source]).strip()

    def _can_fill_destination(self, task: Profile) -> bool:
        # Field names are empty or None
        if not task.source or not task.destination:
            return False

        # The note doesn't have fields with these names
        if task.source not in self._note or task.destination not in self._note:
            return False

        # Yomichan added `No pitch accent data` to the field when creating the note
        if "No pitch accent data".lower() in self._note[task.destination].lower():
            return True

        # Must overwrite any existing data.
        if self._overwrite is True or task.overwrite_destination is True:
            return True

        # Field is empty.
        if not html_to_media_line(self._note[task.destination]):
            return True

        return False


def on_focus_lost(changed: bool, note: Note, field_idx: int) -> bool:
    return DoTasks(
        note=note,
        caller=TaskCaller.focus_lost,
        src_field=note.keys()[field_idx],
    ).run(changed=changed)


def should_generate(note: Note) -> bool:
    """ Generate when a new note is added by Yomichan or Mpvacious. """
    return (
            mw.app.activeWindow() is None
            and note.id == 0
    )


def on_add_note(_col: anki.collection.Collection, note: Note, _deck_id: DeckId) -> None:
    if should_generate(note):
        DoTasks(
            note=note,
            caller=TaskCaller.note_added,
        ).run()


# Entry point
##########################################################################


def init():
    from aqt import gui_hooks

    # Generate when editing a note
    gui_hooks.editor_did_unfocus_field.append(on_focus_lost)

    # Generate when AnkiConnect (Yomichan, Mpvacious) adds a new note.
    hooks.note_will_be_added.append(on_add_note)
