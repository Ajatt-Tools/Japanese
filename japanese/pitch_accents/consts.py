# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import pathlib
from typing import Final

# Paths to the pitch accent files and this particular file
PITCH_DIR_PATH: Final[pathlib.Path] = pathlib.Path(__file__).parent
RES_DIR_PATH: Final[pathlib.Path] = PITCH_DIR_PATH / "res"
FORMATTED_ACCENTS_TSV: Final[pathlib.Path] = RES_DIR_PATH / "pitch_accents_formatted.csv"
FORMATTED_ACCENTS_UPDATED: Final[pathlib.Path] = RES_DIR_PATH / "pitch_accents_formatted.updated"
NO_ACCENT: Final[str] = "?"

# Ensure everything is ok
assert RES_DIR_PATH.is_dir(), "res folder must exist."
assert FORMATTED_ACCENTS_TSV.is_file(), "formatted pitch accents must be present."
