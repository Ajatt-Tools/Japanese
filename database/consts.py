# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

# Paths to the database files and this particular file
THIS_DIR_PATH = os.path.dirname(os.path.normpath(__file__))
DB_DIR_PATH = os.path.join(THIS_DIR_PATH, "res")
DERIVATIVE_PICKLE = os.path.join(DB_DIR_PATH, "formatted_accents_combined.pickle")
NO_ACCENT = "?"
