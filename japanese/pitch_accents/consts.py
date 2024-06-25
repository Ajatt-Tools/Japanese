# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

# Paths to the pitch accent files and this particular file
PITCH_DIR_PATH = os.path.dirname(os.path.normpath(__file__))
RES_DIR_PATH = os.path.join(PITCH_DIR_PATH, "res")
FORMATTED_ACCENTS_TSV = os.path.join(RES_DIR_PATH, "pitch_accents_formatted.csv")
FORMATTED_ACCENTS_PICKLE = os.path.join(RES_DIR_PATH, "pitch_accents_formatted.pickle")
NO_ACCENT = "?"

# Ensure everything is ok
assert os.path.isdir(RES_DIR_PATH), "res folder must exist."
assert os.path.isfile(FORMATTED_ACCENTS_TSV), "formatted pitch accents must be present."
