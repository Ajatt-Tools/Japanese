# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from playground.utils import NoAnkiConfigView
from tests import DATA_DIR


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
