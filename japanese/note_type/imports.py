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
    BundledCodeFile,
    FileVersionTuple,
    version_str_to_tuple,
)
from .consts import CSS_END_TOKEN, CSS_START_TOKEN, JS_SCRIPT_END, JS_SCRIPT_START
from .types import ChangeImportsAction


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


def find_ajt_japanese_code_block_imports(
    template_code: str, *, start_token: str, end_token: str, re_version_comment: re.Pattern
) -> Iterable[CodeBlockInTemplate]:
    idx = 0
    while idx < len(template_code):
        # try to find a script: <script>...</script>
        script = find_block_in_text(template_code, idx, start_token=start_token, end_token=end_token)
        if script is None:
            return

        # collect the entire script
        script_content = template_code[script.start_idx : script.end_idx]

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


class CodeImportManager:
    bundled: BundledCodeFile
    start_token: str
    end_token: str
    re_version_comment: re.Pattern
    re_legacy_import: re.Pattern

    def find_code_imports(self, template_code: str) -> Iterable[CodeBlockInTemplate]:
        return find_ajt_japanese_code_block_imports(
            template_code,
            start_token=self.start_token,
            end_token=self.end_token,
            re_version_comment=self.re_version_comment,
        )

    def ensure_code_in_template(self, template_code: str) -> str:
        # Replace legacy import (if present)
        template_code = re.sub(self.re_legacy_import, "", template_code)
        status_good = False
        # Iterate in reverse to prevent deleting from the beginning and corrupting other ranges.
        for existing_import in reversed(tuple(self.find_code_imports(template_code))):
            if status_good is False and existing_import.version >= self.bundled.version:
                # The existing version happens to be up to date or newer.
                # This is possible if the template has been updated before
                # or a newer version of the add-on has updated the template on a different computer.
                status_good = True
            else:
                # remove an old or duplicate import.
                # remove once. don't affect other imports.
                template_code = template_code[: existing_import.start_idx] + template_code[existing_import.end_idx :]
        if status_good:
            # Found an existing import, and it is up to date.
            # Possible duplicate imports have been removed.
            return template_code.strip()
        # The code was not imported before or the import was old and got removed.
        # Append the current import.
        template_code = f"{template_code.strip()}\n{self.bundled.import_str.strip()}"
        return template_code

    def remove_code_imports(self, html_template: str) -> str:
        # Replace legacy import (if present)
        html_template = re.sub(self.re_legacy_import, "", html_template)
        # Iterate in reverse to prevent deleting from the beginning and corrupting other ranges.
        for existing_import in reversed(tuple(self.find_code_imports(html_template))):
            # Remove every import found.
            html_template = html_template[: existing_import.start_idx] + html_template[existing_import.end_idx :]
        return html_template.strip()


def is_current_code_import_ok(manager: CodeImportManager) -> bool:
    imports = tuple(manager.find_code_imports(manager.bundled.import_str))
    return (
        len(imports) == 1
        and imports[0].version == manager.bundled.version
        and str(imports[0].text_content) == manager.bundled.import_str
    )


# Used to remove CSS imports, thus contains a trailing newline.
RE_AJT_CSS_LEGACY_IMPORT = re.compile(r'@import url\("_ajt_japanese[^()"\']*\.css"\);\n?')
RE_AJT_CSS_VERSION_COMMENT = re.compile(r"\s*/\* AJT Japanese CSS (?P<version>\d+\.\d+\.\d+\.\d+) \*/\n?")

# Charset
RE_CHARSET_RULE = re.compile(r'@charset "UTF-8";\n?', flags=re.MULTILINE | re.IGNORECASE)
CHARSET_RULE = '@charset "UTF-8";'


def ensure_charset_in_css(css_styling: str) -> str:
    # add charset or move it to the top.
    # https://developer.mozilla.org/en-US/docs/Web/CSS/@charset
    css_styling = re.sub(RE_CHARSET_RULE, "", css_styling).strip()
    css_styling = f"{CHARSET_RULE}\n{css_styling}"
    return css_styling


def ensure_css_imports(model_dict: AnkiNoteTypeDict, action: ChangeImportsAction) -> bool:
    """
    Takes a model (note type) and ensures that it imports the bundled CSS file.
    Returns True if the model has been modified and Anki needs to save the changes.
    """
    manager = CSSImportManager()

    if action == ChangeImportsAction.add:
        updated_css = manager.ensure_code_in_template(model_dict["css"])
        updated_css = ensure_charset_in_css(updated_css)
    elif action == ChangeImportsAction.remove:
        updated_css = manager.remove_code_imports(model_dict["css"])
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


class CSSImportManager(CodeImportManager):
    bundled: BundledCodeFile = BUNDLED_CSS_FILE
    start_token: str = CSS_START_TOKEN
    end_token: str = CSS_END_TOKEN
    re_version_comment: re.Pattern = RE_AJT_CSS_VERSION_COMMENT
    re_legacy_import: re.Pattern = RE_AJT_CSS_LEGACY_IMPORT


RE_AJT_JS_LEGACY_IMPORT = re.compile(r'<script [^<>]*src="_ajt_japanese[^"]*\.js"></script>\n?')
RE_AJT_JS_VERSION_COMMENT = re.compile(r"\s*/\* AJT Japanese JS (?P<version>\d+\.\d+\.\d+\.\d+) \*/\n?")


class JSImportManager(CodeImportManager):
    bundled: BundledCodeFile = BUNDLED_JS_FILE
    start_token: str = JS_SCRIPT_START
    end_token: str = JS_SCRIPT_END
    re_version_comment: re.Pattern = RE_AJT_JS_VERSION_COMMENT
    re_legacy_import: re.Pattern = RE_AJT_JS_LEGACY_IMPORT


def ensure_js_imports(template: AnkiCardTemplateDict, side: AnkiCardSide, action: ChangeImportsAction) -> bool:
    """
    Takes a card template (from a note type) and ensures that it imports the bundled JS file.
    Returns True if the template has been modified and Anki needs to save the changes.
    """
    manager = JSImportManager()

    if action == ChangeImportsAction.add:
        updated_template = manager.ensure_code_in_template(template[side])
    elif action == ChangeImportsAction.remove:
        updated_template = manager.remove_code_imports(template[side])
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


# Ensure ok
assert is_current_code_import_ok(JSImportManager())
assert is_current_code_import_ok(CSSImportManager())

print(f"bundled JS version: {BUNDLED_JS_FILE.version_str()}")
print(f"bundled CSS version: {BUNDLED_CSS_FILE.version_str()}")
