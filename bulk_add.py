from typing import Sequence

from aqt import mw
from aqt.browser import Browser
from aqt.qt import *

from .helpers import NoteId, ANKI21_VERSION
from .reading import DoTasks

ACTION_NAME = "AJT: Bulk-add readings"


def bulk_add_readings(nids: Sequence[NoteId]):
    mw.checkpoint(ACTION_NAME)
    mw.progress.start()

    for nid in nids:
        note = mw.col.getNote(nid)
        changed = DoTasks(note=note).run()
        if changed:
            note.flush()

    mw.progress.finish()
    mw.reset()


def setup_browser_menu(browser: Browser):
    """ Add menu entry to browser window """
    action = QAction(ACTION_NAME, browser)
    qconnect(action.triggered, lambda: bulk_add_readings(browser.selectedNotes()))
    browser.form.menuEdit.addAction(action)


def init():
    if ANKI21_VERSION < 45:
        from anki.hooks import addHook
        addHook("browser.setupMenus", setup_browser_menu)
    else:
        from aqt import gui_hooks

        gui_hooks.browser_menus_did_init.append(setup_browser_menu)
