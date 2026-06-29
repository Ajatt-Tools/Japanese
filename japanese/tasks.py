# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import json
from collections.abc import Iterable

import anki.collection
from anki import hooks
from anki.decks import DeckId
from anki.notes import Note
from anki.utils import strip_html_media
from aqt import mw
from aqt.utils import tooltip

from .ajt_common.model_utils import AnkiNoteTypeDict
from .audio import aud_src_mgr
from .audio_manager.download_results import (
    FileSaveResults,
    calc_tooltip_offset,
    format_report_results_msg,
)
from .config_view import JapaneseConfig, get_global_config
from .database.sqlite3_buddy import Sqlite3Buddy
from .furigana.gen_furigana import FuriganaGen
from .helpers.profiles import (
    PitchOutputFormat,
    Profile,
    ProfileAudio,
    ProfileFurigana,
    ProfilePitch,
    TaskCaller,
)
from .pitch_accents.accent_lookup import AccentLookup
from .pitch_artist.add import PitchArtist
from .reading import fgen, format_pronunciations, lookup, pronunciations_to_json


def note_type_matches(note_type: AnkiNoteTypeDict, profile: Profile) -> bool:
    """Return True if the profile's note type name matches the given note type."""
    return profile.note_type.lower() in note_type["name"].lower()


class DoTask:
    """Base class for profile-driven tasks (add furigana, pitch, audio).

    Subclasses are registered automatically via ``__init_subclass__`` and dispatched
    by profile type using ``__new__``.
    """

    _subclasses_map: dict[type[Profile], type["DoTask"]] = {}  # e.g. ProfileFurigana -> AddFurigana
    _key_class_param: str = "task_type"
    _db: Sqlite3Buddy

    def __init_subclass__(cls, **kwargs) -> None:
        """Register each subclass keyed by its profile type."""
        task_type: type[Profile] = kwargs.pop(cls._key_class_param)  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[task_type] = cls

    def __new__(cls, task: Profile, *args, **kwargs) -> "DoTask":
        """Dispatch to the subclass matching the profile type."""
        subclass = cls._subclasses_map[type(task)]
        return object.__new__(subclass)

    def __init__(self, task: Profile, caller: TaskCaller, db: Sqlite3Buddy, cfg: JapaneseConfig) -> None:
        self._task = task
        self._caller = caller
        self._db = db
        self._cfg = cfg

    def _generate_text(self, src_text: str) -> str:
        """Generate output text from the source text. Subclasses must implement this."""
        raise NotImplementedError()

    def run(self, src_text: str, dest_text: str) -> str:
        """Generate text and return it if it differs from both src and dest."""
        if src_text:
            out_text = self._generate_text(src_text)
            if out_text and (not dest_text or out_text != src_text):
                return out_text
        return dest_text


class AddFurigana(DoTask, task_type=ProfileFurigana):
    """Add furigana readings to the source text."""

    _fgen: FuriganaGen
    _task: ProfileFurigana

    def __init__(self, task: Profile, caller: TaskCaller, db: Sqlite3Buddy, cfg: JapaneseConfig) -> None:
        super().__init__(task, caller, db, cfg)
        self._fgen = fgen.with_new_buddy(db)
        assert isinstance(self._task, ProfileFurigana), "AddFurigana task should be initialized with ProfileFurigana"

    def _generate_text(self, src_text: str) -> str:
        """Generate furigana using MeCab for morpheme splitting and the configured color format."""
        return self._fgen.generate_furigana(
            src_text,
            split_morphemes=self._task.split_morphemes,
            output_format=self._task.color_code_pitch,
        )


class AddPitch(DoTask, task_type=ProfilePitch):
    """Add pitch accent data (HTML, JSON, or SVG graphs) to the source text."""

    _lookup: AccentLookup
    _artist: PitchArtist
    _task: ProfilePitch

    def __init__(self, task: Profile, caller: TaskCaller, db: Sqlite3Buddy, cfg: JapaneseConfig) -> None:
        super().__init__(task, caller, db, cfg)
        self._lookup = lookup.with_new_buddy(db)
        self._artist = PitchArtist(self._cfg)
        assert isinstance(self._task, ProfilePitch), "AddPitch task should be initialized with ProfilePitch"

    def _generate_text(self, src_text: str) -> str:
        """Generate pitch accent output in the format specified by the profile."""
        output_format = PitchOutputFormat[self._task.output_format]
        if output_format in (PitchOutputFormat.artist_svg, PitchOutputFormat.artist_colors):
            return self._artist.generate(src_text, output_format=output_format)

        pronunciations = self._lookup.get_pronunciations(src_text, use_mecab=self._task.split_morphemes)
        max_results = self._cfg.pitch_accent.maximum_results

        if output_format == PitchOutputFormat.json:
            return json.dumps(pronunciations_to_json(pronunciations, max_results=max_results), ensure_ascii=False)

        return format_pronunciations(
            pronunciations=pronunciations,
            output_format=output_format,
            sep_single=self._cfg.pitch_accent.reading_separator,
            sep_multi=self._cfg.pitch_accent.word_separator,
            max_results=max_results,
        )


class AddAudio(DoTask, task_type=ProfileAudio):
    """Search, download, and add audio [sound:...] tags to the source text."""

    def _generate_text(self, src_text: str) -> str:
        """Search audio sources, reserve filenames, and kick off background download."""
        session = aud_src_mgr.request_new_session(self._db)
        search_results = session.search_audio(
            src_text,
            split_morphemes=self._task.split_morphemes,
            ignore_inflections=self._cfg.audio_settings.ignore_inflections,
            stop_if_one_source_has_results=self._cfg.audio_settings.stop_if_one_source_has_results,
        )[: self._cfg.audio_settings.maximum_results]
        # Pre-reserve filenames so that [sound:...] tags use the actual (normalized) names.
        audio_tags, reserved = session.reserve_and_format_tags(search_results)
        # "Download and save" has to run on main as it will launch a new QueryOp.
        assert mw, "Anki should be running."
        mw.taskman.run_on_main(
            functools.partial(
                session.download_reserved,
                reserved,
                on_finish=self._report_results,
            )
        )
        return audio_tags

    def _report_results(self, r: FileSaveResults) -> None:
        """Show a tooltip with audio download results."""
        if not self._caller.cfg.audio_download_report:
            return
        if txt := format_report_results_msg(r):
            tooltip(txt, period=7000, y_offset=calc_tooltip_offset(len(r.successes) + len(r.fails)))


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
    """Orchestrates running all applicable profiles against a single note."""

    _note: Note
    _caller: TaskCaller
    _src_field: str | None
    _overwrite: bool

    def __init__(
        self,
        note: Note,
        *,
        cfg: JapaneseConfig,
        caller: TaskCaller,
        src_field: str | None = None,
        overwrite: bool = False,
    ) -> None:
        """Initialize with the note, config, caller context, and optional source field filter."""
        self._note = note
        self._cfg = cfg
        self._caller = caller
        self._src_field = src_field
        self._overwrite = overwrite

    def iter_tasks(self, note: Note, src_field: str | None = None) -> Iterable[Profile]:
        """Yield profiles whose note type matches and whose source field matches (if specified)."""
        note_type = note.note_type()
        assert note_type
        for profile in self._cfg.iter_profiles():
            if note_type_matches(note_type, profile) and (src_field is None or profile.source == src_field):
                yield profile

    def run(self, changed: bool = False) -> bool:
        """Execute all applicable tasks for the note and return whether any field changed."""
        with Sqlite3Buddy() as db:
            for task in self.iter_tasks(self._note, self._src_field):
                if task.should_answer_to(self._caller) and task.applies_to_note(self._note):
                    changed = self._do_task(task, db) or changed
            return changed

    def _do_task(self, task: Profile, db: Sqlite3Buddy) -> bool:
        """Execute a single task: clear garbage, generate text, and write to the destination field."""
        changed = False

        if self._field_contains_garbage(task.destination):
            self._note[task.destination] = ""  # immediately clear garbage
            changed = True

        if self._can_fill_destination(task) and (src_text := self._src_text(task)):
            self._note[task.destination] = DoTask(
                task,
                self._caller,
                db,
                self._cfg,
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
        assert mw and mw.col, "Collection must be open."
        return mw.col.media.strip(self._note[task.source]).strip()

    def _field_contains_garbage(self, field_name: str) -> bool:
        """
        Rikaitan added `No pitch accent data` to the field when creating the note.
        Rikaitan doesn't have this problem.
        """
        return "No pitch accent data".lower() in self._note[field_name].lower()


def should_generate(note: Note) -> bool:
    """Generate when a new note is added by Rikaitan or Mpvacious."""
    assert mw
    return mw.app.activeWindow() is None and note.id == 0


class Tasks:
    """Registers Anki hooks for automatic generation on focus loss and note addition."""

    _cfg: JapaneseConfig

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Store config for hook callbacks."""
        self._cfg = cfg

    def on_add_note(self, _col: anki.collection.Collection, note: Note, _deck_id: DeckId) -> None:
        """Hook callback: generate fields when a new note is added by AnkiConnect."""
        if should_generate(note):
            DoTasks(
                note=note,
                cfg=self._cfg,
                caller=TaskCaller.note_added,
            ).run()

    def on_focus_lost(self, changed: bool, note: Note, field_idx: int) -> bool:
        """Hook callback: generate fields when the editor loses focus on a field."""
        return DoTasks(
            note=note,
            cfg=self._cfg,
            caller=TaskCaller.focus_lost,
            src_field=note.keys()[field_idx],
        ).run(changed=changed)


# Entry point
##########################################################################


def init() -> None:
    """Register Anki hooks for furigana, pitch, and audio generation."""
    from aqt import gui_hooks

    cfg = get_global_config()
    mw._ajt__japanese_tasks = tasks = Tasks(cfg)

    # Generate when editing a note
    gui_hooks.editor_did_unfocus_field.append(tasks.on_focus_lost)

    # Generate when AnkiConnect (Rikaitan, Mpvacious) adds a new note.
    hooks.note_will_be_added.append(tasks.on_add_note)
