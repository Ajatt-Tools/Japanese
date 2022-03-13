# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import dataclasses
import enum
from typing import Dict, Any, List, Optional, NamedTuple, Iterable

import aqt
from anki.notes import Note


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    note_type: str
    source: str
    destination: str
    mode: str

    @classmethod
    def new(cls):
        return cls(
            name="New profile",
            note_type="Japanese",
            source="VocabKanji",
            destination="VocabPitchPattern",
            mode="html",
        )


@enum.unique
class TaskMode(enum.Enum):
    number = enum.auto()
    html = enum.auto()
    furigana = enum.auto()


class Task(NamedTuple):
    src_field: str
    dst_field: str
    mode: TaskMode


def profile_matches(note_type: Dict[str, Any], profile: Profile) -> bool:
    return profile.note_type.lower() in note_type['name'].lower()


def get_notetype(note: Note) -> Dict[str, Any]:
    if hasattr(note, 'note_type'):
        return note.note_type()
    else:
        return note.model()


def iter_tasks(note: Note, src_field: Optional[str] = None) -> Iterable[Task]:
    note_type = get_notetype(note)
    for profile in list_profiles():
        if profile_matches(note_type, profile) and (src_field is None or profile.source == src_field):
            yield Task(profile.source, profile.destination, TaskMode[profile.mode])


def get_config():
    return aqt.mw.addonManager.getConfig(__name__)


def write_config():
    return aqt.mw.addonManager.writeConfig(__name__, config)


def list_profiles() -> List[Profile]:
    return [Profile(**p) for p in config['profiles']]


config = get_config()
