# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    # https://github.com/beartype/beartype
    from beartype.claw import beartype_this_package

    beartype_this_package()
except ImportError:
    pass

import sys

from aqt import mw


def start_addon() -> None:
    from . import (
        bulk_add,
        context_menu,
        editor_toolbar,
        gui,
        kanjigrid_addon,
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
    kanjigrid_addon.init()


if mw and "pytest" not in sys.modules:
    start_addon()
