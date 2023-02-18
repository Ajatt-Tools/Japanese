# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os.path
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


def resolve_file(*paths) -> str:
    """ Return path to file inside the add-on's dir. """
    parent_dir = os.path.abspath(os.path.dirname(__file__))

    while not os.path.samefile(np := os.path.dirname(parent_dir), aqt.mw.pm.addonFolder()):
        parent_dir = np

    return os.path.join(parent_dir, *paths)
