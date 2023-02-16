from typing import NewType, Dict, Any

import aqt

try:
    from anki.notes import NoteId
except ImportError:
    NoteId = NewType("NoteId", int)

from anki.notes import Note
ANKI21_VERSION = int(aqt.appVersion.split('.')[-1])
LONG_VOWEL_MARK = 'ー'


def ui_translate(key: str) -> str:
    return key.capitalize().replace('_', ' ')


def get_notetype(note: Note) -> Dict[str, Any]:
    if hasattr(note, 'note_type'):
        return note.note_type()
    else:
        return note.model()
