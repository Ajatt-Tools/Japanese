# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re

from .bundled_files import BUNDLED_CSS_FILE, BUNDLED_JS_FILE

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese[^"]*\.css"\);')
RE_AJT_JS_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>')

assert re.fullmatch(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str)
assert re.fullmatch(RE_AJT_JS_IMPORT, BUNDLED_JS_FILE.import_str)


def ensure_css_in_card(css_styling: str) -> str:
    # The CSS was imported previously, but a new version has been released.
    css_styling = re.sub(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str, css_styling)
    if BUNDLED_CSS_FILE.import_str not in css_styling:
        # The CSS was not imported before. Likely a fresh Note Type or Anki install.
        css_styling = f'{BUNDLED_CSS_FILE.import_str}\n{css_styling}'
    return css_styling


def ensure_css_imported(model_dict: dict[str, str]) -> bool:
    """
    Takes a model (note type) and ensures that it imports the bundled CSS file.
    Returns True if the model has been modified and Anki needs to save the changes.
    """
    if (updated_css := ensure_css_in_card(model_dict["css"])) != model_dict["css"]:
        model_dict["css"] = updated_css
        return True
    return False


def ensure_js_in_card_side(html_template: str) -> str:
    # The JS was imported previously, but a new version has been released.
    html_template = re.sub(RE_AJT_JS_IMPORT, "", html_template)
    if BUNDLED_JS_FILE.import_str not in html_template:
        # The JS was not imported before. Likely a fresh Note Type or Anki install.
        html_template = f"{html_template.strip()}\n{BUNDLED_JS_FILE.import_str}"
    return html_template


def ensure_js_imported(template: dict[str, str], side: str) -> bool:
    """
    Takes a card template (from a note type) and ensures that it imports the bundled JS file.
    Returns True if the template has been modified and Anki needs to save the changes.
    """
    if (template_text := ensure_js_in_card_side(template[side])) != template[side]:
        # Template was modified
        template[side] = template_text
        return True
    return False
