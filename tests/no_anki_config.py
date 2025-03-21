# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json
import pathlib

import pytest

from japanese.config_view import JapaneseConfig
from tests import DATA_DIR


class NoAnkiConfigView(JapaneseConfig):
    """
    Loads the default config without starting Anki.
    """

    config_json_path = pathlib.Path(__file__).parent.parent / "japanese" / "config.json"

    def _set_underlying_dicts(self) -> None:
        with open(self.config_json_path) as f:
            self._default_config = self._config = json.load(f)


@pytest.fixture(scope="session")
def no_anki_config() -> NoAnkiConfigView:
    config = NoAnkiConfigView()
    config.furigana["maximum_results"] = 1
    # substitute audio sources
    config["audio_sources"] = [
        {
            "enabled": True,
            "name": "TAAS-TEST",
            "url": str(DATA_DIR / "taas_index.json"),
        },
    ]
    return config
