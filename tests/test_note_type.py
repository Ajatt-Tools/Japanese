# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
from typing import Optional

import pytest

from japanese.ajt_common.model_utils import (
    AnkiCardSide,
    AnkiCardTemplateDict,
    AnkiNoteTypeDict,
)
from japanese.note_type.bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    UNK_VERSION,
    FileVersionTuple,
    version_str_to_tuple,
)
from japanese.note_type.files_in_col_media import FileInCollection
from japanese.note_type.imports import (
    CHARSET_RULE,
    ensure_css_imports,
    ensure_js_imports,
    find_block_in_text,
    find_existing_css_version,
    is_current_js_ok,
    Range,
)
from japanese.note_type.types import ChangeImportsAction

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_name() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


def test_parse_version() -> None:
    assert version_str_to_tuple("25.5.15.99") == FileVersionTuple(25, 5, 15, 99)
    assert version_str_to_tuple("0.0.0.0") == FileVersionTuple(0, 0, 0, 0)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (
            # Import is missing.
            """@import url("_file.css");\nbody { color: pink; }""",
            None,
        ),
        (
            # Legacy import found.
            """@import url("_file.css");\n@import url("_ajt_japanese.css");\nbody { color: pink; }""",
            UNK_VERSION,
        ),
        (
            # Version specified
            """@import url("_file.css");\n@import url("_ajt_japanese_1.1.1.1.css");\nbody { color: pink; }""",
            (1, 1, 1, 1),
        ),
        (
            # Version specified
            """@import url("_file.css");\n@import url("_ajt_japanese_12.12.12.12.css");\nbody { color: pink; }""",
            (12, 12, 12, 12),
        ),
    ],
)
def test_find_existing_css_version(test_input: str, expected: Optional[FileVersionTuple]) -> None:
    assert find_existing_css_version(test_input) == expected


@pytest.mark.parametrize(
    "css_styling, is_added, added_css, is_removed, removed_css",
    [
        (
            # Import is missing.
            """/* NO CSS */""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* NO CSS */",
            False,
            None,
        ),
        (
            # Charset is declared.
            f"""{CHARSET_RULE}\n/*Other CSS*/""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/*Other CSS*/",
            False,
            None,
        ),
        (
            # Legacy import found.
            """@import url("_ajt_japanese.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */",
            True,
            """/* Other CSS */""",
        ),
        (
            # Older version
            """/* Other CSS */\n@import url("_ajt_japanese_1.1.1.1.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */",
            True,
            """/* Other CSS */\n/* Other CSS */""",
        ),
        (
            # Current version
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */\n/* Other CSS */\n",
            False,
            None,
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n/* Other CSS */\n",
        ),
        (
            # Newer version
            f"""{CHARSET_RULE}\n/* Other CSS */\n@import url("_ajt_japanese_999.1.1.1.css");\n/* Other CSS */""",
            False,
            None,
            True,
            f"""{CHARSET_RULE}\n/* Other CSS */\n/* Other CSS */""",
        ),
    ],
)
def test_css_imports(
    css_styling: str, is_added: bool, added_css: Optional[str], is_removed: bool, removed_css: Optional[str]
) -> None:
    def make_model_dict() -> AnkiNoteTypeDict:
        return {"css": css_styling, "name": "pytest", "tmpls": [], "flds": []}

    model_dict = make_model_dict()
    assert ensure_css_imports(model_dict, action=ChangeImportsAction.add) is is_added
    assert model_dict["css"] == (added_css or css_styling)

    model_dict = make_model_dict()
    assert ensure_css_imports(model_dict, action=ChangeImportsAction.remove) is is_removed
    assert model_dict["css"] == (removed_css or css_styling)


NO_JS = """\
<!-- some template code -->
<div>
    <span>some html</span>
    <span>some html</span>
</div>\
"""

OLD_VER = """\
<script>
    /* AJT Japanese JS 24.7.14.0 */
    //some old code
    function z() {}
</script>\
"""


@pytest.mark.parametrize(
    "template_html, is_added, added_html, is_removed, removed_html",
    [
        (
            # Import is missing.
            NO_JS,
            True,
            f"{NO_JS}\n{BUNDLED_JS_FILE.import_str}",
            False,
            None,
        ),
        (
            # Legacy import found (script defer).
            """<!-- begin -->\n<script defer src="_ajt_japanese_24.7.14.2.js"></script>\n<!-- end -->""",
            True,
            f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}",
            True,
            """<!-- begin -->\n<!-- end -->""",
        ),
        (
            # Legacy import found.
            """<!-- begin -->\n<script src="_ajt_japanese.js"></script>\n<!-- end -->""",
            True,
            f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}",
            True,
            """<!-- begin -->\n<!-- end -->""",
        ),
        (
            # Older version
            f"{OLD_VER}\n<!-- after old import -->",
            True,
            f"<!-- after old import -->\n{BUNDLED_JS_FILE.import_str}",
            True,
            f"<!-- after old import -->",
        ),
        (
            # Older version (but it is formatted)
            f"<!--whatever-->\n\n{OLD_VER}\n<!--whatever-->",
            True,
            f"<!--whatever-->\n\n<!--whatever-->\n{BUNDLED_JS_FILE.import_str}",
            True,
            f"<!--whatever-->\n\n<!--whatever-->",
        ),
        (
            # Current version
            f"<!-- before current JS -->\n{BUNDLED_JS_FILE.import_str}\n<!-- after current JS -->",
            False,
            None,
            True,
            f"<!-- before current JS -->\n<!-- after current JS -->",
        ),
        (
            # Current version (repeated for some reason)
            # Remove the duplicate imports.
            f"""\
<!-- template text 1 -->
{BUNDLED_JS_FILE.import_str}
<!-- template text 2 -->
{BUNDLED_JS_FILE.import_str}
<!-- template text 3 -->
{BUNDLED_JS_FILE.import_str}\
""",
            True,
            f"""\
<!-- template text 1 -->
<!-- template text 2 -->
<!-- template text 3 -->
{BUNDLED_JS_FILE.import_str}\
""",
            True,
            f"""\
<!-- template text 1 -->
<!-- template text 2 -->
<!-- template text 3 -->\
""",
        ),
        (
            # Current version (repeated for some reason)
            # Remove the duplicate imports.
            f"{NO_JS}\n{BUNDLED_JS_FILE.import_str}\n{BUNDLED_JS_FILE.import_str}\n{NO_JS}\n{BUNDLED_JS_FILE.import_str}\n{NO_JS}",
            True,
            f"{NO_JS}\n{NO_JS}\n{BUNDLED_JS_FILE.import_str}\n{NO_JS}",
            True,
            f"{NO_JS}\n{NO_JS}\n{NO_JS}",
        ),
        (
            # Older version and current version
            f"{NO_JS}\n{OLD_VER}\n{BUNDLED_JS_FILE.import_str}\n{OLD_VER}\n{NO_JS}",
            True,
            f"{NO_JS}\n{BUNDLED_JS_FILE.import_str}\n{NO_JS}",
            True,
            f"{NO_JS}\n{NO_JS}",
        ),
        (
            # Newer version
            "<script>\n/* AJT Japanese JS 999.1.1.1 */\n//some new code\n</script>\n<!--whatever-->",
            False,
            None,
            True,
            "<!--whatever-->",
        ),
    ],
)
def test_js_imports(
    template_html: str, is_added: bool, added_html: Optional[str], is_removed: bool, removed_html: Optional[str]
) -> None:
    side: AnkiCardSide = "qfmt"

    def make_template_dict() -> AnkiCardTemplateDict:
        return {side: template_html, "name": "pytest"}

    template_dict: AnkiCardTemplateDict = make_template_dict()
    assert ensure_js_imports(template_dict, side, action=ChangeImportsAction.add) is is_added
    assert template_dict[side] == (added_html or template_html)

    template_dict: AnkiCardTemplateDict = make_template_dict()
    assert ensure_js_imports(template_dict, side, action=ChangeImportsAction.remove) is is_removed
    assert template_dict[side] == (removed_html or template_html)


@pytest.mark.parametrize(
    "file_name, expected_ver",
    [
        (
            # no version
            "_ajt_japanese.css",
            UNK_VERSION,
        ),
        (
            # js files are not stored in collection (anymore)
            "_ajt_japanese.js",
            UNK_VERSION,
        ),
        (
            # has version
            "_ajt_japanese_1.1.1.1.css",
            (1, 1, 1, 1),
        ),
        (
            # js files are not stored in collection (anymore)
            "_ajt_japanese_1.1.1.1.js",
            UNK_VERSION,
        ),
        (
            # has version
            "_ajt_japanese_99.99.99.99.css",
            (99, 99, 99, 99),
        ),
    ],
)
def test_file_in_collection(file_name: str, expected_ver: FileVersionTuple) -> None:
    # all files start with '_ajt_japanese'
    assert FileInCollection.new(file_name).version == expected_ver


@pytest.mark.parametrize(
    "text, cursor_idx, start_token, end_token, expected",
    [
        # Basic block found
        ("abc<script>content</script>def", 0, "<script>", "</script>", Range(3, 27)),
        # Block with newline after end token
        ("<script>content</script>\n", 0, "<script>", "</script>", Range(0, 25)),
        # Start token not found
        ("no block here", 0, "<script>", "</script>", None),
        # End token not found
        ("<script>content", 0, "<script>", "</script>", None),
        # Cursor after start token, should not find
        ("abc<script>content</script>def", 10, "<script>", "</script>", None),
        # Multiple blocks, find first
        ("<script>first</script><script>second</script>", 0, "<script>", "</script>", Range(0, 22)),
        # Cursor at second block
        ("<script>first</script><script>second</script>", 22, "<script>", "</script>", Range(22, 45)),
        # Empty text
        ("", 0, "<script>", "</script>", None),
        # Tokens that are substrings
        ("aaabbbccc", 0, "aa", "cc", Range(0, 8)),
        # Verify newline inclusion only when immediately after end token
        ("<script>content</script>extra", 0, "<script>", "</script>", Range(0, 24)),
        ("<script>content</script>\nextra", 0, "<script>", "</script>", Range(0, 25)),
        # Edge case: multiple newlines after end token, only first included
        ("<script>content</script>\n\n", 0, "<script>", "</script>", Range(0, 25)),
    ],
)
def test_find_block_in_text(
    text: str,
    cursor_idx: int,
    start_token: str,
    end_token: str,
    expected: Optional[Range],
) -> None:
    result = find_block_in_text(text, cursor_idx, start_token=start_token, end_token=end_token)
    assert result == expected


def test_is_bundled_ok() -> None:
    assert is_current_js_ok()
