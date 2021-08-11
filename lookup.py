# -*- coding: utf-8 -*-

from collections import OrderedDict
from gettext import gettext as _

from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.utils import showInfo, disable_help_button, restoreGeom, saveGeom
from aqt.webview import AnkiWebView

from .helpers import *
from .nhk_pronunciation import get_pronunciations, format_pronunciations

ACTION_NAME = "Pitch accent lookup"

HTML = """
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8" />
    <title>Pronunciations</title>
    <style>
        body {
            box-sizing: border-box;
            font-size: 25px;
            font-family: "Noto Serif",
                "Noto Serif CJK JP",
                "Yu Mincho",
                "Liberation Serif",
                "Times New Roman",
                Times,
                Georgia,
                Serif;
            background-color: #FFFAF0;
            color: #2A1B0A;
            line-height: 1.4;
            text-align: left;

            display: grid;
            grid-template-columns: max-content 1fr;
            row-gap: 8px;
            column-gap: 8px
        }

        .key {
            color: #582020;
        }

        .key,
        .value {
            margin-top: 0px;
            margin-bottom: 0px;
        }
    </style>
</head>

<body>%s</body>

</html>
"""


def format_pronunciations_rich(pronunciations: Dict[str, List[str]]):
    ordered_dict = OrderedDict()
    for key, html_entries in pronunciations.items():
        ordered_dict[key] = ''.join(f'<li>{v}</li>' for v in html_entries)

    entries = []
    for k, v in ordered_dict.items():
        entries.append(f'<div class="key">{k}</div><ol class="value">{v}</ol>')

    return HTML % ''.join(entries)


class ViewPitchAccentsDialog(QDialog):
    def __init__(self, parent: QWidget, selected_text: str):
        QDialog.__init__(self, parent)
        self.webview = AnkiWebView(parent=self, title=ACTION_NAME)
        self.pronunciations = get_pronunciations(selected_text)
        self._setup_ui()

    def _setup_ui(self):
        mw.garbage_collect_on_dialog_finish(self)
        disable_help_button(self)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(ACTION_NAME)
        self.setMinimumSize(420, 240)

        self.webview.setHtml(format_pronunciations_rich(self.pronunciations))
        layout = QVBoxLayout()
        layout.addWidget(self.webview)
        layout.addLayout(self.make_buttons())
        self.setLayout(layout)
        restoreGeom(self, ACTION_NAME)

    def reject(self) -> None:
        self.webview = None
        saveGeom(self, ACTION_NAME)
        QDialog.reject(self)

    def accept(self) -> None:
        self.webview = None
        saveGeom(self, ACTION_NAME)
        QDialog.accept(self)

    def make_buttons(self):
        buttons = (
            ('Ok', self.accept),
            ('Copy HTML to Clipboard', lambda: QApplication.clipboard().setText(format_pronunciations(
                self.pronunciations,
                sep_single='、',
                sep_multi='<br>',
                expr_sep='：'
            )))
        )
        hbox = QHBoxLayout()
        for label, action in buttons:
            button = QPushButton(label)
            qconnect(button.clicked, action)
            hbox.addWidget(button)
        hbox.addStretch()
        return hbox


def on_lookup_pronunciation(parent: QWidget, text: str):
    """ Do a lookup on the selection """
    if text := text.strip():
        ViewPitchAccentsDialog(parent, text).exec_()
    else:
        showInfo(_("Empty selection."))


def create_menu() -> QAction:
    """ Add a hotkey and menu entry """
    lookup_action = QAction(ACTION_NAME, mw)
    qconnect(lookup_action.triggered, lambda: on_lookup_pronunciation(mw, mw.web.selectedText()))
    if config["lookupShortcut"]:
        lookup_action.setShortcut(config["lookupShortcut"])
    return lookup_action


def add_context_menu_item(webview: AnkiWebView, menu: QMenu):
    menu.addAction(ACTION_NAME, lambda: on_lookup_pronunciation(webview, webview.selectedText()))


def init():
    # Create the manual look-up menu entry
    mw.form.menuTools.addAction(create_menu())
    gui_hooks.editor_will_show_context_menu.append(add_context_menu_item)
    gui_hooks.webview_will_show_context_menu.append(add_context_menu_item)
