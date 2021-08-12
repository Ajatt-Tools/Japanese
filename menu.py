from aqt import mw
from aqt.qt import *

from .gui import create_options_action
from .lookup import create_lookup_action


def menu_root_entry() -> QMenu:
    if not hasattr(mw.form, 'ajt_root_menu'):
        mw.form.ajt_root_menu = QMenu('AJT', mw)
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.form.ajt_root_menu)
    return mw.form.ajt_root_menu


def init():
    root_menu = menu_root_entry()
    root_menu.addAction(create_lookup_action(root_menu))
    root_menu.addAction(create_options_action(root_menu))
