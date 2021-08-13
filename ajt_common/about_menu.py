# -*- coding: utf-8 -*-
#
# Copyright: (C) 2021 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
from aqt import mw
from aqt.qt import *
from aqt.utils import disable_help_button
from aqt.webview import AnkiWebView

from .consts import *


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget):
        super(AboutDialog, self).__init__(parent=parent or mw)
        disable_help_button(self)
        mw.garbage_collect_on_dialog_finish(self)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(f'{DIALOG_NAME} {ADDON_SERIES}')
        self.setSizePolicy(self.make_size_policy())
        self.setMinimumSize(320, 240)
        self.setLayout(self.make_root_layout())

    def make_about_webview(self, html_content: str) -> AnkiWebView:
        webview = AnkiWebView(parent=self)
        webview.setProperty("url", QUrl("about:blank"))
        webview.stdHtml(html_content, js=[])
        webview.setMinimumSize(480, 360)
        return webview

    def make_button_box(self) -> QWidget:
        button_box = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        return button_box

    def make_root_layout(self) -> QLayout:
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.make_about_webview(ABOUT_MSG))
        root_layout.addWidget(self.make_button_box())
        root_layout.setContentsMargins(0, 0, 0, 0)
        return root_layout

    def make_size_policy(self) -> QSizePolicy:
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        return size_policy


def menu_root_entry() -> QMenu:
    if not hasattr(mw.form, 'ajt_root_menu'):
        mw.form.ajt_root_menu = QMenu(ADDON_SERIES, mw)
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.form.ajt_root_menu)
        mw.form.ajt_root_menu.addAction(create_about_action(mw.form.ajt_root_menu))
        mw.form.ajt_root_menu.addSeparator()
    return mw.form.ajt_root_menu


def create_about_action(parent: QWidget) -> QAction:
    def open_about_dialog():
        dialog = AboutDialog(mw)
        return dialog.exec_()

    action = QAction(f'{DIALOG_NAME}...', parent)
    qconnect(action.triggered, open_about_dialog)
    return action
