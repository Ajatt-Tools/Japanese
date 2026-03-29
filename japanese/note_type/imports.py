# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
import typing
from collections.abc import Iterable
from typing import Optional

from ..ajt_common.model_utils import (
    AnkiCardSide,
    AnkiCardTemplateDict,
    AnkiNoteTypeDict,
)
from .bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    UNK_VERSION,
    FileVersionTuple,
    version_str_to_tuple,
)
from .types import ChangeImportsAction

RE_AJT_CSS_IMPORT = re.compile(r'@import url\("_ajt_japanese(?:_(?P<version>\d+\.\d+\.\d+\.\d+))?\.css"\);')

# Used to remove CSS imports, thus contains a trailing newline.
RE_AJT_CSS_IMPORT_SIMPLE = re.compile(r'@import url\("_ajt_japanese[^()"\']*\.css"\);\n?')

RE_AJT_JS_LEGACY_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>\n?')
RE_AJT_JS_VERSION_COMMENT = re.compile(r"\s*/\* AJT Japanese JS (?P<version>\d+\.\d+\.\d+\.\d+) \*/\n?")
RE_CHARSET_RULE = re.compile(r'@charset "UTF-8";\n?', flags=re.MULTILINE | re.IGNORECASE)
CHARSET_RULE = '@charset "UTF-8";'


class JavaScriptImport(typing.NamedTuple):
    version: FileVersionTuple
    text_content: str
    start_idx: int
    end_idx: int


class Range(typing.NamedTuple):
    start_idx: int
    end_idx: int


def find_js_in_template(html_template: str, cursor_idx: int) -> Optional[Range]:
    script_start_token = "<script>"
    script_end_token = "</script>"

    # try to find an opening script tag
    script_start_idx = html_template.find(script_start_token, cursor_idx)
    if script_start_idx < 0:
        return None

    # move cursor behind the opening tag.
    # <script>xxx
    #         ^
    # try to find a closing script tag
    script_end_idx = html_template.find(script_end_token, script_start_idx + len(script_start_token))
    if script_end_idx < 0:
        return None

    # move cursor behind the closing tag.
    # </script>xxx
    #          ^
    script_end_idx = script_end_idx + len(script_end_token)

    # Handle newline after the script.
    # In case the script has to be removed from the html template later, it should be removed with the newline.
    if script_end_idx < len(html_template) and html_template[script_end_idx] == "\n":
        script_end_idx += 1

    return Range(script_start_idx, script_end_idx)


def find_ajt_japanese_js_imports(html_template: str) -> Iterable[JavaScriptImport]:
    idx = 0
    while idx < len(html_template):
        # try to find a script: <script>...</script>
        script = find_js_in_template(html_template, idx)
        if script is None:
            return

        # collect the entire script
        script_content = html_template[script.start_idx : script.end_idx]

        # Try to find out if this is the AJT Japanese JS by searching for its version.
        if m := re.search(RE_AJT_JS_VERSION_COMMENT, script_content):
            yield JavaScriptImport(
                version=version_str_to_tuple(m.group("version")),
                text_content=script_content,
                start_idx=script.start_idx,
                end_idx=script.end_idx,
            )

        # move cursor behind the closing tag.
        idx = script.end_idx


def find_existing_css_version(css_styling: str) -> Optional[FileVersionTuple]:
    existing_import = re.search(RE_AJT_CSS_IMPORT, css_styling)
    if not existing_import:
        return None
    existing_version = existing_import.group("version")
    if not existing_version:
        return UNK_VERSION
    return version_str_to_tuple(existing_import.group("version"))


def ensure_css_in_card(css_styling: str) -> str:
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


def ensure_js_in_card_side(html_template: str) -> str:
    # Replace legacy import (if present)
    html_template = re.sub(RE_AJT_JS_LEGACY_IMPORT, "", html_template)
    status_good = False
    # Iterate in reverse to prevent deleting from the beginning and corrupting other ranges.
    for existing_import in reversed(tuple(find_ajt_japanese_js_imports(html_template))):
        if status_good is False and existing_import.version >= BUNDLED_JS_FILE.version:
            # The existing version happens to be up to date or newer.
            # This is possible if the template has been updated before
            # or a newer version of the add-on has updated the template on a different computer.
            status_good = True
        else:
            # remove an old or duplicate import.
            # remove once. don't affect other imports.
            html_template = html_template[: existing_import.start_idx] + html_template[existing_import.end_idx :]
    if status_good:
        # Found an existing import, and it is up to date.
        # Possible duplicate imports have been removed.
        return html_template.strip()
    # The JavaScript was not imported before or the import was old and got removed.
    # Append the current JS import.
    html_template = f"{html_template.strip()}\n{BUNDLED_JS_FILE.import_str.strip()}"
    return html_template


def remove_js_imports(html_template: str) -> str:
    # Replace legacy import (if present)
    html_template = re.sub(RE_AJT_JS_LEGACY_IMPORT, "", html_template)
    # Iterate in reverse to prevent deleting from the beginning and corrupting other ranges.
    for existing_import in reversed(tuple(find_ajt_japanese_js_imports(html_template))):
        # Remove every import found.
        html_template = html_template[: existing_import.start_idx] + html_template[existing_import.end_idx :]
    return html_template.strip()


def ensure_js_imports(template: AnkiCardTemplateDict, side: AnkiCardSide, action: ChangeImportsAction) -> bool:
    """
    Takes a card template (from a note type) and ensures that it imports the bundled JS file.
    Returns True if the template has been modified and Anki needs to save the changes.
    """
    if action == ChangeImportsAction.add:
        updated_template = ensure_js_in_card_side(template[side])
    elif action == ChangeImportsAction.remove:
        updated_template = remove_js_imports(template[side])
    else:
        raise ValueError(f"invalid action: {action}")

    if updated_template != template[side]:
        # Template was modified
        template[side] = updated_template
        print(
            f"Template '{template['name']}': JS has been "
            f" {'updated' if action == ChangeImportsAction.add else 'trimmed'}."
        )
        return True
    else:
        print(f"Template '{template['name']}': JS unchanged.")
    return False


def is_current_js_ok() -> bool:
    imports = tuple(find_ajt_japanese_js_imports(BUNDLED_JS_FILE.import_str))
    return (
        len(imports) == 1
        and imports[0].version == BUNDLED_JS_FILE.version
        and str(imports[0].text_content) == BUNDLED_JS_FILE.import_str
    )


assert is_current_js_ok()
assert re.fullmatch(RE_AJT_CSS_IMPORT, BUNDLED_CSS_FILE.import_str)
print(f"bundled JS version: {BUNDLED_JS_FILE.version_str()}")
print(f"bundled CSS version: {BUNDLED_CSS_FILE.version_str()}")
