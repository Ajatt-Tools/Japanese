# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json

from aqt import AnkiQt, mw
from aqt.qt import *

from .ajt_common.about_menu import menu_root_entry
from .ajt_common.addon_config import AddonConfigManager
from .config_view import config_view as cfg
from .helpers.file_ops import find_file_in_parents
from .kanjigrid.config_util import KanjiGridConfigProxy
from .kanjigrid.kanjigrid import ACTION_NAME, KanjiGrid


class AJTKanjiGridConfigProxy(KanjiGridConfigProxy):
    def __init__(self, mwref: AnkiQt, mgr: AddonConfigManager) -> None:
        super().__init__(mwref)
        self.mgr = mgr

    def _get_config_dict(self) -> dict:
        kanjigrid_default_config_path = find_file_in_parents("kanjigrid/config.json")
        with open(kanjigrid_default_config_path, encoding="utf8") as f:
            default_dict = json.load(f)
        for key, value in default_dict.items():
            if key not in self.mgr["kanjigrid"]:
                self.mgr["kanjigrid"][key] = value
        return self.mgr["kanjigrid"]

    def _write_config_dict(self, config: dict) -> None:
        self.mgr["kanjigrid"].update(config)
        self.mgr.write_config()


def init() -> None:
    root_menu = menu_root_entry()
    gen_grid_action = QAction(f"🈷️ {ACTION_NAME}...", root_menu)
    root_menu.addAction(gen_grid_action)
    mw.kanjigrid = KanjiGrid(cfg=AJTKanjiGridConfigProxy(mw, cfg), menu_action=gen_grid_action)
