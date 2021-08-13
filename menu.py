# -*- coding: utf-8 -*-
#
# Copyright: (C) 2021 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#

from aqt import mw
from aqt.qt import *

from .helpers import ADDON_SERIES
from .gui import create_options_action
from .lookup import create_lookup_action


def menu_root_entry() -> QMenu:
    if not hasattr(mw.form, 'ajt_root_menu'):
        mw.form.ajt_root_menu = QMenu(ADDON_SERIES, mw)
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.form.ajt_root_menu)
    return mw.form.ajt_root_menu


def init():
    root_menu = menu_root_entry()
    root_menu.addAction(create_lookup_action(root_menu))
    root_menu.addAction(create_options_action(root_menu))
