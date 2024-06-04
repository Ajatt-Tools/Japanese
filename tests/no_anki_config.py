# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json

from japanese.ajt_common.addon_config import AddonConfigABC
from japanese.helpers.file_ops import find_config_json


class NoAnkiConfigView(AddonConfigABC):
    """
    Loads the default config without starting Anki.
    """

    def __init__(self):
        with open(find_config_json()) as f:
            self._config = json.load(f)

    @property
    def config(self) -> dict:
        return self._config

    @property
    def default_config(self) -> dict:
        return self._config
