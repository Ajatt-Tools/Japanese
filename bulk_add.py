# -*- coding: utf-8 -*-

from typing import Sequence

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *

from .helpers import *
from .nhk_pronunciation import fill_destination

ACTION_NAME = "Bulk-add pitch accents"


def bulk_add_pitch_accents(nids: Sequence):
    mw.checkpoint(ACTION_NAME)
    mw.progress.start()

    for note in (note for nid in nids if is_supported_notetype(note := mw.col.getNote(nid))):
        if any([fill_destination(note, src_field, dst_field) for src_field, dst_field in iter_fields()]):
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
