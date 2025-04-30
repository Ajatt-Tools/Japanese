# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys

from aqt import mw


def start_addon() -> None:
    from . import (
        bulk_add,
        context_menu,
        editor_toolbar,
        gui,
        lookup_dialog,
        tasks,
        welcome_dialog,
    )
    from .helpers.webview_utils import anki_addon_set_web_exports
    from .note_type import note_type

    # Ensure that css and other resources are loaded.
    anki_addon_set_web_exports()

    tasks.init()
    lookup_dialog.init()
    bulk_add.init()
    gui.init()
    context_menu.init()
    editor_toolbar.init()
    welcome_dialog.init()
    note_type.init()


if mw and "pytest" not in sys.modules:
    start_addon()
