# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re

from .bundled_files import BUNDLED_CSS_FILE, BUNDLED_JS_FILE

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese[^"]*\.css"\);')
RE_AJT_JS_IMPORT = re.compile(r'<script defer src="_ajt_japanese[^"]*\.js"></script>')

assert re.fullmatch(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str)
assert re.fullmatch(RE_AJT_JS_IMPORT, BUNDLED_JS_FILE.import_str)


def ensure_css_imported(model_dict: dict[str, str]) -> bool:
    """
    Takes a model (note type) and ensures that it imports the bundled CSS file.
    Returns True if the model has been modified and Anki needs to save the changes.
    """
    updated_css = re.sub(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str, model_dict["css"])
    if updated_css != model_dict["css"]:
        # The CSS was imported previously, but a new version has been released.
        model_dict["css"] = updated_css
        return True
    if BUNDLED_CSS_FILE.import_str not in model_dict["css"]:
        # The CSS was not imported before. Likely a fresh Note Type or Anki install.
        model_dict["css"] = f'{BUNDLED_CSS_FILE.import_str}\n{model_dict["css"]}'
        return True
    return False


def ensure_js_imported(template: dict[str, str], side: str) -> bool:
    """
    Takes a card template (from a note type) and ensures that it imports the bundled JS file.
    Returns True if the template has been modified and Anki needs to save the changes.
    """
    updated_js = re.sub(RE_AJT_JS_IMPORT, BUNDLED_JS_FILE.import_str, template[side])
    if updated_js != template[side]:
        # The JS was imported previously, but a new version has been released.
        template[side] = updated_js
        return True
    if BUNDLED_JS_FILE.import_str not in template[side]:
        # The JS was not imported before. Likely a fresh Note Type or Anki install.
        template[side] = f"{template[side]}\n{BUNDLED_JS_FILE.import_str}"
        return True
    return False
