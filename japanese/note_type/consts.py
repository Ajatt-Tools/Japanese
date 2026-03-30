# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

# JS and CSS that the add-on includes in the user's notes.
THIS_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
AJT_JAPANESE_JS_PATH = os.path.join(THIS_DIR_PATH, "_ajt_japanese.js")
AJT_JAPANESE_CSS_PATH = os.path.join(THIS_DIR_PATH, "_ajt_japanese.css")

# Ensure everything is ok
assert os.path.isfile(AJT_JAPANESE_JS_PATH), "Add-on JS must be present."
assert os.path.isfile(AJT_JAPANESE_CSS_PATH), "Add-on CSS must be present."

JS_SCRIPT_START = "<script>"
JS_SCRIPT_END = "</script>"

CSS_START_TOKEN = "/* === AJT Japanese CSS BLOCK START === */"
CSS_END_TOKEN = "/* === AJT Japanese CSS BLOCK END === */"
