# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

# Paths to the pitch accent files and this particular file
THIS_DIR_PATH = os.path.dirname(os.path.normpath(__file__))
RES_DIR_PATH = os.path.join(THIS_DIR_PATH, "res")
FORMATTED_ACCENTS_PICKLE = os.path.join(RES_DIR_PATH, "formatted_accents_combined.pickle")
NO_ACCENT = "?"
