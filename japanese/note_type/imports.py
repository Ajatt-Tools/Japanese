# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
import typing
from collections.abc import Iterable
from typing import Optional

from .css_imports import RE_AJT_CSS_IMPORT
from ..ajt_common.model_utils import (
    AnkiCardSide,
    AnkiCardTemplateDict,
)
from .bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    FileVersionTuple,
    version_str_to_tuple,
)
from .types import ChangeImportsAction

# Used to remove CSS imports, thus contains a trailing newline.

RE_AJT_JS_LEGACY_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>\n?')
RE_AJT_JS_VERSION_COMMENT = re.compile(r"\s*/\* AJT Japanese JS (?P<version>\d+\.\d+\.\d+\.\d+) \*/\n?")


class CodeBlockInTemplate(typing.NamedTuple):
    """
    A code block (e.g. a <script> tag) found in an Anki card HTML template, along with its version.
    """
    version: FileVersionTuple
    text_content: str
    start_idx: int
    end_idx: int


class Range(typing.NamedTuple):
    start_idx: int
    end_idx: int


def find_block_in_text(text: str, cursor_idx: int, *, start_token: str, end_token: str) -> Optional[Range]:
    # try to find the start token (e.g. an opening script tag)
    block_start_idx = text.find(start_token, cursor_idx)
    if block_start_idx < 0:
        return None

    # move cursor behind the start token (e.g. an opening script tag).
    # <script>xxx
    #         ^
    # try to find the end token
    block_end_idx = text.find(end_token, block_start_idx + len(start_token))
    if block_end_idx < 0:
        return None

    # move cursor behind the end token (e.g. a closing script tag).
    # </script>xxx
    #          ^
    block_end_idx = block_end_idx + len(end_token)

    # Handle newline after the block.
    # In case the block has to be removed from the HTML template later, it should be removed with the newline.
    if block_end_idx < len(text) and text[block_end_idx] == "\n":
        block_end_idx += 1

    return Range(block_start_idx, block_end_idx)


def find_js_in_template(html_template: str, cursor_idx: int) -> Optional[Range]:
    return find_block_in_text(
        html_template,
        cursor_idx,
        start_token="<script>",
        end_token="</script>"
    )


def find_ajt_japanese_code_block_imports(template_code: str, *, start_token: str, end_token: str, re_version_comment: re.Pattern) -> Iterable[CodeBlockInTemplate]:
    idx = 0
    while idx < len(template_code):
        # try to find a script: <script>...</script>
        script = find_block_in_text(template_code, idx, start_token=start_token, end_token=end_token)
        if script is None:
            return

        # collect the entire script
        script_content = template_code[script.start_idx: script.end_idx]

        # Try to find out if this is the AJT Japanese JS by searching for its version.
        if m := re.search(re_version_comment, script_content):
            yield CodeBlockInTemplate(
                version=version_str_to_tuple(m.group("version")),
                text_content=script_content,
                start_idx=script.start_idx,
                end_idx=script.end_idx,
            )

        # move cursor behind the closing tag.
        idx = script.end_idx


def find_ajt_japanese_js_imports(html_template: str) -> Iterable[CodeBlockInTemplate]:
    return find_ajt_japanese_code_block_imports(
        html_template,
        start_token="<script>",
        end_token="</script>",
        re_version_comment=RE_AJT_JS_VERSION_COMMENT,
    )


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
