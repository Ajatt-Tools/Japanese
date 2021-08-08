# -*- coding: utf-8 -*-
from collections import OrderedDict
from gettext import gettext as _

from aqt import gui_hooks
from aqt.qt import *
from aqt.utils import showInfo
from aqt.webview import AnkiWebView

from .helpers import *
from .nhk_pronunciation import get_pronunciations, format_pronunciations

CONTEXT_MENU_ITEM_NAME = "NHK pitch accent lookup"

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


def create_webview_dialog(selected_text: str) -> QDialog:
    pronunciations = get_pronunciations(selected_text)

    dialog = QDialog(parent=mw)
    dialog.setWindowTitle(CONTEXT_MENU_ITEM_NAME)
    dialog.setMinimumSize(480, 480)

    webview = AnkiWebView(parent=dialog, title=CONTEXT_MENU_ITEM_NAME)
    webview.setHtml(format_pronunciations_rich(pronunciations))

    layout = QVBoxLayout()
    layout.addWidget(webview)

    def make_buttons():
        buttons = (
            ('Ok', dialog.accept),
            ('Copy HTML to Clipboard', lambda: QApplication.clipboard().setText(format_pronunciations(
                pronunciations,
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

    layout.addLayout(make_buttons())
    dialog.setLayout(layout)
    return dialog


def on_lookup_pronunciation(text: str = None):
    """ Do a lookup on the selection """
    if text or len(text := mw.web.selectedText().strip()) > 0:
        create_webview_dialog(text).exec_()
    else:
        showInfo(_("Empty selection."))


def create_menu() -> QAction:
    """ Add a hotkey and menu entry """
    lookup_action = QAction(CONTEXT_MENU_ITEM_NAME, mw)
    qconnect(lookup_action.triggered, on_lookup_pronunciation)
    if config["lookupShortcut"]:
        lookup_action.setShortcut(config["lookupShortcut"])
    return lookup_action


def init():
    # Create the manual look-up menu entry
    mw.form.menuTools.addAction(create_menu())
