# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import math
from typing import NewType, Dict, Any, TypeVar, Sequence, Iterable

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


def get_notetype(note: Note) -> dict[str, Any]:
    if hasattr(note, 'note_type'):
        return note.note_type()
    else:
        return note.model()


T = TypeVar("T")


def split_list(input_list: Sequence[T], n_chunks: int) -> Iterable[Sequence[T]]:
    """ Splits a list into N chunks. """
    chunk_size = math.ceil(len(input_list) / n_chunks)
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]


if __name__ == '__main__':
    assert (list(split_list([1, 2, 3], n_chunks=2)) == [[1, 2], [3]])
    assert (list(split_list([1, 2, 3, 4], n_chunks=2)) == [[1, 2], [3, 4]])
    assert (list(split_list([1, 2, 3, 4, 5], n_chunks=2)) == [[1, 2, 3], [4, 5]])
    assert (list(split_list([1, 2, 3, 4, 5, 6, 7], n_chunks=2)) == [[1, 2, 3, 4], [5, 6, 7]])
    assert (list(split_list([1, 2, 3, 4, 5, 6, 7, 8], n_chunks=3)) == [[1, 2, 3], [4, 5, 6], [7, 8]])
    print("Passed.")
