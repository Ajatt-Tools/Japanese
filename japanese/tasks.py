# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import io
from collections.abc import Iterable
from typing import Optional

import anki.collection
from anki import hooks
from anki.decks import DeckId
from anki.models import NotetypeDict
from anki.notes import Note
from anki.utils import strip_html_media
from aqt import mw
from aqt.utils import tooltip

from .audio import FileSaveResults, aud_src_mgr, format_audio_tags
from .audio_manager.basic_types import FileUrlData
from .config_view import config_view as cfg
from .furigana.gen_furigana import FuriganaGen
from .helpers.profiles import (
    PitchOutputFormat,
    Profile,
    ProfileAudio,
    ProfileFurigana,
    ProfilePitch,
    TaskCaller,
)
from .helpers.sqlite3_buddy import Sqlite3Buddy
from .pitch_accents.accent_lookup import AccentLookup
from .reading import fgen, format_pronunciations, lookup


def note_type_matches(note_type: NotetypeDict, profile: Profile) -> bool:
    return profile.note_type.lower() in note_type["name"].lower()


def iter_tasks(note: Note, src_field: Optional[str] = None) -> Iterable[Profile]:
    note_type = note.note_type()
    assert note_type
    for profile in cfg.iter_profiles():
        if note_type_matches(note_type, profile) and (src_field is None or profile.source == src_field):
            yield profile


class DoTask:
    _subclasses_map: dict[type[Profile], type["DoTask"]] = {}  # e.g. ProfileFurigana -> AddFurigana
    _key_class_param: str = "task_type"
    _db: Sqlite3Buddy

    def __init_subclass__(cls, **kwargs) -> None:
        task_type: type[Profile] = kwargs.pop(cls._key_class_param)  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[task_type] = cls

    def __new__(cls, task: Profile, *args, **kwargs):
        subclass = cls._subclasses_map[type(task)]
        return object.__new__(subclass)

    def __init__(self, task, caller: TaskCaller, db: Sqlite3Buddy) -> None:
        self._task = task
        self._caller = caller
        self._db = db

    def _generate_text(self, src_text: str) -> str:
        raise NotImplementedError()

    def run(self, src_text: str, dest_text: str) -> str:
        if src_text:
            out_text = self._generate_text(src_text)
            if out_text and (not dest_text or out_text != src_text):
                return out_text
        return dest_text


class AddFurigana(DoTask, task_type=ProfileFurigana):
    def _generate_text(self, src_text: str) -> str:
        return fgen.generate_furigana(
            src_text,
            split_morphemes=self._task.split_morphemes,
            output_format=self._task.color_code_pitch,
        )


class AddPitch(DoTask, task_type=ProfilePitch):
    def _generate_text(self, src_text: str) -> str:
        return format_pronunciations(
            pronunciations=lookup.get_pronunciations(src_text, use_mecab=self._task.split_morphemes),
            output_format=PitchOutputFormat[self._task.output_format],
            sep_single=cfg.pitch_accent.reading_separator,
            sep_multi=cfg.pitch_accent.word_separator,
        )


class AddAudio(DoTask, task_type=ProfileAudio):
    def _generate_text(self, src_text: str) -> str:
        session = aud_src_mgr.request_new_session(self._db)
        search_results = session.search_audio(
            src_text,
            split_morphemes=self._task.split_morphemes,
            ignore_inflections=cfg.audio_settings.ignore_inflections,
            stop_if_one_source_has_results=cfg.audio_settings.stop_if_one_source_has_results,
        )[: cfg.audio_settings.maximum_results]
        # "Download and save tags" has to run on main as it will launch a new QueryOp.
        assert mw
        mw.taskman.run_on_main(
            functools.partial(
                session.download_and_save_tags,
                search_results,
                on_finish=self._report_results,
            )
        )
        return format_audio_tags(search_results)

    def _report_results(self, r: FileSaveResults):
        """
        Show a tooltip with audio download results.
        """
        if not self._caller.cfg.audio_download_report:
            return
        buffer = io.StringIO()
        if r.successes:
            buffer.write(f"<b>Added {len(r.successes)} files to the collection.</b><ol>")
            buffer.write("".join(f"<li>{file.desired_filename}</li>" for file in r.successes))
            buffer.write("</ol>")
        if r.fails:
            buffer.write(f"<b>Failed {len(r.fails)} files.</b><ol>")
            buffer.write(
                "".join(
                    f"<li>{fail.file.desired_filename}: {fail.describe_short()}</li>"
                    for fail in r.fails
                    if isinstance(fail.file, FileUrlData)
                )
            )
            buffer.write("</ol>")
        if txt := buffer.getvalue():
            return tooltip(txt, period=7000, y_offset=80 + 18 * (len(r.successes) + len(r.fails)))


def html_to_media_line(txt: str) -> str:
    """Strip HTML but keep media filenames."""
    return strip_html_media(
        txt.replace("<br>", " ")
        .replace("<br/>", " ")
        .replace("<br />", " ")
        .replace("<div>", " ")
        .replace("</div>", " ")
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

        with Sqlite3Buddy() as db:
            for task in self._tasks:
                if task.should_answer_to(self._caller) and task.applies_to_note(self._note):
                    changed = self._do_task(task, db) or changed
            return changed

    def _do_task(self, task: Profile, db: Sqlite3Buddy) -> bool:
        changed = False

        if self._field_contains_garbage(task.destination):
            self._note[task.destination] = ""  # immediately clear garbage
            changed = True

        if self._can_fill_destination(task) and (src_text := self._src_text(task)):
            self._note[task.destination] = DoTask(
                task,
                self._caller,
                db,
            ).run(
                src_text,
                self._note[task.destination],
            )
            changed = True
        return changed

    def _can_fill_destination(self, task: Profile) -> bool:
        """
        The add-on can fill the destination field if it's empty
        or if the user wants to fill it with new data and erase the old data.
        """
        return self._is_overwrite_permitted(task) or not html_to_media_line(self._note[task.destination])

    def _is_overwrite_permitted(self, task: Profile) -> bool:
        """
        Has the user allowed the add-on to erase existing content (if any) in the destination field?
        """
        return self._overwrite or task.overwrite_destination

    def _src_text(self, task: Profile) -> str:
        """
        Return source text with sound and image tags removed.
        """
        assert mw
        return mw.col.media.strip(self._note[task.source]).strip()

    def _field_contains_garbage(self, field_name: str) -> bool:
        """
        Yomichan added `No pitch accent data` to the field when creating the note.
        Rikaitan doesn't have this problem.
        """
        return "No pitch accent data".lower() in self._note[field_name].lower()


def on_focus_lost(changed: bool, note: Note, field_idx: int) -> bool:
    return DoTasks(
        note=note,
        caller=TaskCaller.focus_lost,
        src_field=note.keys()[field_idx],
    ).run(changed=changed)


def should_generate(note: Note) -> bool:
    """Generate when a new note is added by Yomichan or Mpvacious."""
    assert mw
    return mw.app.activeWindow() is None and note.id == 0


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
