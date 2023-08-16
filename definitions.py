# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import requests
from aqt.editor import Editor

from .config_view import config_view as cfg
from .helpers.sakura_client import SakuraParisClient, AddDefBehavior, DEF_SEP


class SakuraParisAnkiClient(SakuraParisClient):
    def add_definition(self, editor: Editor):
        """
        Interaction with Anki's editor.
        """
        from aqt.utils import tooltip
        if self._config.source not in editor.note:
            return tooltip(f"Note doesn't have field \"{self._config.source}\".")
        if not editor.note[self._config.source]:
            return tooltip(f"Field \"{self._config.source}\" is empty.")
        try:
            definition = self.fetch_def(editor.note[self._config.source])
        except requests.exceptions.ConnectionError:
            return tooltip("Connection error.")
        else:
            if not definition:
                return tooltip("Nothing found.")
            editor.note[self._config.destination] = (
                definition
                if self._config.behavior == AddDefBehavior.replace
                else f"{editor.note[self._config.destination]}{DEF_SEP}{definition}"
                if self._config.behavior == AddDefBehavior.append
                else f"{definition}{DEF_SEP}{editor.note[self._config.destination]}"
            ).removeprefix(DEF_SEP).removesuffix(DEF_SEP)


# Entry point
##########################################################################

sakura_client = SakuraParisAnkiClient(cfg.definitions)
