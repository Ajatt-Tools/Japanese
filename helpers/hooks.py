# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Callable, List

import anki.collection
import anki.hooks
from anki.notes import Note


class CollectionWillAddNote:
    _hooks: list[Callable[[Note], None]] = []

    def __init__(self):
        anki.collection.Collection.add_note = anki.hooks.wrap(
            old=anki.collection.Collection.add_note,
            new=self._on_add_note,
            pos='before',
        )

    def append(self, callback: Callable[[Note], None]) -> None:
        self._hooks.append(callback)

    def _on_add_note(self, _col, note: Note, _did) -> None:
        for hook in self._hooks:
            hook(note)


collection_will_add_note = CollectionWillAddNote()
