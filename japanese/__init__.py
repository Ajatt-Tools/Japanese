# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys


def start_addon():
    from . import tasks, lookup, bulk_add, gui, context_menu, editor_toolbar

    tasks.init()
    lookup.init()
    bulk_add.init()
    gui.init()
    context_menu.init()
    editor_toolbar.init()


if "pytest" not in sys.modules:
    start_addon()
