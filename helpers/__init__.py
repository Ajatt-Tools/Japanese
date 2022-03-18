from typing import NewType

import aqt

try:
    from anki.notes import NoteId
except ImportError:
    NoteId = NewType("NoteId", int)

ANKI21_VERSION = int(aqt.appVersion.split('.')[-1])
LONG_VOWEL_MARK = 'ー'


def ui_translate(key: str) -> str:
    return key.capitalize().replace('_', ' ')
