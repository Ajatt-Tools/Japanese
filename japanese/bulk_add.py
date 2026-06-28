# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence

from anki.collection import Collection, OpChanges
from anki.notes import Note, NoteId
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.operations import CollectionOp
from aqt.qt import *
from aqt.utils import showInfo

from .config_view import JapaneseConfig, get_global_config
from .helpers.consts import ADDON_NAME
from .helpers.profiles import TaskCaller
from .tasks import DoTasks

ACTION_NAME = f"{ADDON_NAME}: Bulk-generate"


class BulkConverter:
    _cfg: JapaneseConfig
    _browser: Browser

    def __init__(self, cfg: JapaneseConfig, browser: Browser) -> None:
        self._cfg = cfg
        self._browser = browser

    def _update_notes_op(self, col: Collection, notes: Sequence[Note]) -> OpChanges:
        pos = col.add_custom_undo_entry(f"{ADDON_NAME}: Add data to {len(notes)} notes.")
        to_update = []
        for note in notes:
            changed = DoTasks(note=note, cfg=self._cfg, caller=TaskCaller.bulk_add).run()
            if changed:
                to_update.append(note)
        col.update_notes(to_update)
        return col.merge_undo_entries(pos)

    def bulk_add_readings(self, nids: Sequence[NoteId]) -> None:
        CollectionOp(
            parent=self._browser,
            op=lambda col: self._update_notes_op(col, notes=[mw.col.get_note(nid) for nid in nids]),
        ).success(
            lambda out: showInfo(
                parent=self._browser,
                title="Tasks done",
                textFormat="rich",
                text=f"Processed {len(nids)} selected notes.",
            )
        ).run_in_background()


def setup_browser_menu(browser: Browser) -> None:
    """Add menu entry to browser window"""
    action = QAction(ACTION_NAME, browser)
    cfg = get_global_config()
    # Note: attach the object to the browser to prevent it from being deleted. Otherwise, the menu action doesn't work.
    browser._ajt__japanese_bulk_converter = bulk = BulkConverter(cfg, browser)
    qconnect(action.triggered, lambda: bulk.bulk_add_readings(browser.selectedNotes()))
    browser.form.menuEdit.addAction(action)


def init() -> None:
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
