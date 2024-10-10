# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import io
import re
from typing import Optional

from .bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    UNK_VERSION,
    FileVersionTuple,
    VersionedFile,
    version_str_to_tuple,
)

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese[^"]*\.css"\);')
RE_AJT_JS_LEGACY_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>\n?')
RE_AJT_JS_VERSION_COMMENT = re.compile(r"/\* AJT Japanese JS (?P<version>\d+\.\d+\.\d+\.\d+) \*/\n?")


def find_ajt_japanese_js_import(template_text: str) -> Optional[VersionedFile]:
    buffer = io.StringIO()

    class Status(enum.Enum):
        none = 0
        found_script = 1
        identified_ajt_script = 2

    status = Status.none
    version: FileVersionTuple = UNK_VERSION

    for line in template_text.splitlines(keepends=True):
        if line == "<script>\n":
            status = Status.found_script
        elif (m := re.fullmatch(RE_AJT_JS_VERSION_COMMENT, line)) and status == Status.found_script:
            status = Status.identified_ajt_script
            version = version_str_to_tuple(m.group("version"))
            buffer.write("<script>\n")
            buffer.write(line)
        elif line.strip() == "</script>" and status == Status.identified_ajt_script:
            buffer.write(line)
            return VersionedFile(version, buffer.getvalue())
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
        html_template = html_template.replace(existing_import.text_content.strip(), BUNDLED_JS_FILE.import_str.strip())
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


assert find_ajt_japanese_js_import(BUNDLED_JS_FILE.import_str) == VersionedFile(
    BUNDLED_JS_FILE.version,
    BUNDLED_JS_FILE.import_str,
)
assert re.fullmatch(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str)
