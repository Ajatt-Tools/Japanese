# -*- coding: utf-8 -*-

from gettext import gettext as _

from aqt.qt import *
from aqt.utils import showInfo, showText

from .helpers import *
from .nhk_pronunciation import get_formatted_pronunciations

HTML = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<html>
<head>
<style> body { font-size: 24px; } </style>
<title>Pronunciations</title>
<meta charset="UTF-8" />
</head>
<body>%s</body>
</html>
"""


def on_lookup_pronunciation():
    """ Do a lookup on the selection """
    if len(text := mw.web.selectedText().strip()) > 0:
        showText(
            HTML % get_formatted_pronunciations(text, "・", "<br/><br/>\n", ": "),
            type="html"
        )
    else:
        showInfo(_("Empty selection."))


def create_menu() -> QAction:
    """ Add a hotkey and menu entry """
    lookup_action = QAction("NHK pitch accent lookup", mw)
    qconnect(lookup_action.triggered, on_lookup_pronunciation)
    if config["lookupShortcut"]:
        lookup_action.setShortcut(config["lookupShortcut"])
    return lookup_action


def init():
    # Create the manual look-up menu entry
    mw.form.menuTools.addAction(create_menu())
