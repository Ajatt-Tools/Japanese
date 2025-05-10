# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib
from typing import Final

from ..helpers.file_ops import user_files_dir

# Paths to the pitch accent files
PITCH_DIR_PATH: Final[pathlib.Path] = pathlib.Path(__file__).parent
RES_DIR_PATH: Final[pathlib.Path] = PITCH_DIR_PATH / "res"
FORMATTED_ACCENTS_TSV: Final[pathlib.Path] = RES_DIR_PATH / "pitch_accents_formatted.csv"
NO_ACCENT: Final[str] = "?"
SMALL_KANA_CHARS: Final[str] = "ァィゥェォャュョぁぃぅぇぉゃゅょ"

# User dir
USER_DATA_CSV_PATH: Final[pathlib.Path] = pathlib.Path(user_files_dir()) / "user_data.tsv"
FORMATTED_ACCENTS_UPDATED: Final[pathlib.Path] = pathlib.Path(user_files_dir()) / "pitch_accents_formatted.updated"

# Ensure everything is ok
assert RES_DIR_PATH.is_dir(), "res folder must exist."
assert FORMATTED_ACCENTS_TSV.is_file(), "formatted pitch accents must be present."
