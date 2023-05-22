# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Sequence

from anki.collection import Collection
from anki.notes import Note
from aqt import mw
from aqt.browser import Browser
from aqt.operations import CollectionOp
from aqt.qt import *
from aqt.utils import showInfo

from .config_view import config_view as cfg
from .helpers import NoteId
from .helpers.profiles import TaskCaller
from .tasks import DoTasks

ACTION_NAME = "AJT: Bulk-generate"


def update_notes_op(col: Collection, notes: Sequence[Note]):
    pos = col.add_custom_undo_entry(f"AJT: Add data to {len(notes)} notes.")
    to_update = []
    for note in notes:
        changed = DoTasks(note=note, caller=TaskCaller.bulk_add, overwrite=cfg.regenerate_readings).run()
        if changed:
            to_update.append(note)
    col.update_notes(to_update)
    return col.merge_undo_entries(pos)


def bulk_add_readings(nids: Sequence[NoteId], parent: Browser):
    CollectionOp(
        parent=parent, op=lambda col: update_notes_op(col, notes=[mw.col.get_note(nid) for nid in nids])
    ).success(
        lambda out: showInfo(
            parent=parent,
            title="Task done",
            textFormat="rich",
            text=f"Added data to {len(nids)} selected notes."
        )
    ).run_in_background()


def setup_browser_menu(browser: Browser):
    """ Add menu entry to browser window """
    action = QAction(ACTION_NAME, browser)
    qconnect(action.triggered, lambda: bulk_add_readings(browser.selectedNotes(), parent=browser))
    browser.form.menuEdit.addAction(action)


def init():
    from aqt import gui_hooks

    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
