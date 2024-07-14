# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import io
import re
from typing import Optional

from .bundled_files import BUNDLED_CSS_FILE, BUNDLED_JS_FILE

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese[^"]*\.css"\);')
RE_AJT_JS_LEGACY_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>\n?')


def find_ajt_japanese_js_import(template_text: str) -> Optional[str]:
    buffer = io.StringIO()

    class Status(enum.Enum):
        none = 0
        found_script = 1
        identified_ajt_script = 2

    status = Status.none
    for line in template_text.splitlines(keepends=True):
        if line == "<script>\n":
            status = Status.found_script
        elif line.startswith("/* AJT Japanese JS ") and line.endswith(" */\n") and status == Status.found_script:
            status = Status.identified_ajt_script
            buffer.write("<script>\n")
            buffer.write(line)
        elif line.strip() == "</script>" and status == Status.identified_ajt_script:
            buffer.write(line)
            return buffer.getvalue()
        elif status == Status.identified_ajt_script:
            buffer.write(line)
    return None


def ensure_css_in_card(css_styling: str) -> str:
    # The CSS was imported previously, but a new version has been released.
    css_styling = re.sub(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str, css_styling)
    if BUNDLED_CSS_FILE.import_str not in css_styling:
        # The CSS was not imported before. Likely a fresh Note Type or Anki install.
        css_styling = f"{BUNDLED_CSS_FILE.import_str}\n{css_styling}"
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
    # Replace legacy import (if present)
    html_template = re.sub(RE_AJT_JS_LEGACY_IMPORT, "", html_template)
    if existing_import := find_ajt_japanese_js_import(html_template):
        # The JS was imported previously, but a new version has been released.
        html_template = html_template.replace(existing_import.strip(), BUNDLED_JS_FILE.import_str.strip())
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


assert find_ajt_japanese_js_import(BUNDLED_JS_FILE.import_str) == BUNDLED_JS_FILE.import_str
assert re.fullmatch(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str)
