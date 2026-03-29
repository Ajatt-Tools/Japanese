# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
from typing import Optional

from japanese.ajt_common.model_utils import AnkiNoteTypeDict
from japanese.note_type.bundled_files import FileVersionTuple, UNK_VERSION, version_str_to_tuple, BUNDLED_CSS_FILE
from japanese.note_type.types import ChangeImportsAction

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese(?:_(?P<version>\d+\.\d+\.\d+\.\d+))?\.css"\);')
RE_AJT_CSS_IMPORT_SIMPLE = re.compile(r'@import url\("_ajt_japanese[^()"\']*\.css"\);\n?')
RE_CHARSET_RULE = re.compile(r'@charset "UTF-8";\n?', flags=re.MULTILINE | re.IGNORECASE)
CHARSET_RULE = '@charset "UTF-8";'


def find_existing_css_version(css_styling: str) -> Optional[FileVersionTuple]:
    existing_import = re.search(RE_AJT_CSS_IMPORT, css_styling)
    if not existing_import:
        return None
    existing_version = existing_import.group("version")
    if not existing_version:
        return UNK_VERSION
    return version_str_to_tuple(existing_import.group("version"))


def ensure_css_in_card(css_styling: str) -> str:
    css_styling = re.sub(RE_AJT_CSS_IMPORT_SIMPLE, "", css_styling)


    existing_version = find_existing_css_version(css_styling)
    if existing_version is not None and existing_version >= BUNDLED_CSS_FILE.version:
        # The import is added and the version is up-to-date (or newer).
        return css_styling

    # The CSS was imported previously, but a new version has been released.
    css_styling = re.sub(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str, css_styling)

    if BUNDLED_CSS_FILE.import_str not in css_styling:
        # The CSS was not imported before. Likely a fresh Note Type or Anki install.
        css_styling = f"{BUNDLED_CSS_FILE.import_str}\n{css_styling}"

    # add charset or move it to the top.
    # https://developer.mozilla.org/en-US/docs/Web/CSS/@charset
    css_styling = re.sub(RE_CHARSET_RULE, "", css_styling).strip()
    css_styling = f"{CHARSET_RULE}\n{css_styling}"

    return css_styling


def remove_css_import(css_template: str) -> str:
    return re.sub(RE_AJT_CSS_IMPORT_SIMPLE, "", css_template)


def ensure_css_imports(model_dict: AnkiNoteTypeDict, action: ChangeImportsAction) -> bool:
    """
    Takes a model (note type) and ensures that it imports the bundled CSS file.
    Returns True if the model has been modified and Anki needs to save the changes.
    """
    if action == ChangeImportsAction.add:
        updated_css = ensure_css_in_card(model_dict["css"])
    elif action == ChangeImportsAction.remove:
        updated_css = remove_css_import(model_dict["css"])
    else:
        raise ValueError(f"invalid action: {action}")

    if updated_css != model_dict["css"]:
        model_dict["css"] = updated_css
        print(
            f"Model '{model_dict['name']}': CSS has been"
            f" {'updated' if action == ChangeImportsAction.add else 'trimmed'}."
        )
        return True
    else:
        print(f"Model '{model_dict['name']}': CSS template unchanged.")
    return False
