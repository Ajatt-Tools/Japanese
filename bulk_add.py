from typing import Sequence

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *

from .helpers.config import iter_tasks
from .helpers import NoteId
from .reading import do_tasks

ACTION_NAME = "Bulk-add pitch accents"


def bulk_add_pitch_accents(nids: Sequence[NoteId]):
    mw.checkpoint(ACTION_NAME)
    mw.progress.start()

    for nid in nids:
        note = mw.col.getNote(nid)
        changed = do_tasks(note=note, tasks=iter_tasks(note))
        if changed:
            note.flush()

    mw.progress.finish()
    mw.reset()


def setup_browser_menu(browser: Browser):
    """ Add menu entry to browser window """
    action = QAction(ACTION_NAME, browser)
    qconnect(action.triggered, lambda: bulk_add_pitch_accents(browser.selectedNotes()))
    browser.form.menuEdit.addAction(action)


def init():
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
