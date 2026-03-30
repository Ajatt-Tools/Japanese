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
    EDIT_WARN,
    UNK_VERSION,
    FileVersionTuple,
    VersionedFile,
    inline_bundled_css,
    inline_bundled_js,
    version_str_to_tuple,
    wrap_bundled_css,
    wrap_bundled_js,
)
from japanese.note_type.consts import (
    CSS_END_TOKEN,
    CSS_START_TOKEN,
    JS_SCRIPT_END,
    JS_SCRIPT_START,
)
from japanese.note_type.files_in_col_media import FileInCollection
from japanese.note_type.imports import (
    CHARSET_RULE,
    CSSImportManager,
    JSImportManager,
    Range,
    ensure_css_imports,
    ensure_js_imports,
    find_block_in_text,
    is_current_code_import_ok,
)
from japanese.note_type.types import ChangeImportsAction

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_name() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


def test_parse_version() -> None:
    assert version_str_to_tuple("25.5.15.99") == FileVersionTuple(25, 5, 15, 99)
    assert version_str_to_tuple("0.0.0.0") == FileVersionTuple(0, 0, 0, 0)


@pytest.mark.parametrize(
    "css_styling, is_added, added_css, is_removed, removed_css",
    [
        (
            # Import is missing.
            """/* NO CSS */""",
            True,
            f"{CHARSET_RULE}\n/* NO CSS */\n{BUNDLED_CSS_FILE.import_str}",
            False,
            None,
        ),
        (
            # Charset is declared.
            f"""{CHARSET_RULE}\n/*Other CSS*/""",
            True,
            f"{CHARSET_RULE}\n/*Other CSS*/\n{BUNDLED_CSS_FILE.import_str}",
            False,
            None,
        ),
        (
            # Legacy import found.
            """@import url("_ajt_japanese.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}",
            True,
            """/* Other CSS */""",
        ),
        (
            # Older legacy @import version (treated as legacy, stripped and re-added as inline)
            """/* Other CSS */\n@import url("_ajt_japanese_1.1.1.1.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}",
            True,
            """/* Other CSS */\n/* Other CSS */""",
        ),
        (
            # Current version (inline CSS block already present and up to date)
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */\n/* Other CSS */",
            False,
            None,
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n/* Other CSS */",
        ),
        (
            # Newer legacy @import version (treated as legacy, stripped and re-added as inline)
            f"""{CHARSET_RULE}\n/* Other CSS */\n@import url("_ajt_japanese_999.1.1.1.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}",
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
    assert is_current_code_import_ok(JSImportManager())
    assert is_current_code_import_ok(CSSImportManager())


def test_wrap_bundled_css_structure() -> None:
    """Verify wrap_bundled_css() produces correctly delimited output."""
    result = wrap_bundled_css("body { color: red; }", "1.2.3.4")
    assert result.startswith(CSS_START_TOKEN)
    assert result.endswith(CSS_END_TOKEN)
    assert "/* AJT Japanese CSS 1.2.3.4 */" in result
    assert "body { color: red; }" in result
    assert (
        result
        == f"{CSS_START_TOKEN}\n/* AJT Japanese CSS 1.2.3.4 */\n{EDIT_WARN}\nbody {{ color: red; }}\n{CSS_END_TOKEN}"
    )


def test_wrap_bundled_js_structure() -> None:
    """Verify wrap_bundled_js() produces correctly delimited output."""
    result = wrap_bundled_js("console.log('hi');", "5.6.7.8")
    assert result.startswith(JS_SCRIPT_START)
    assert result.endswith(JS_SCRIPT_END)
    assert "/* AJT Japanese JS 5.6.7.8 */" in result
    assert "console.log('hi');" in result
    assert (
        result == f"{JS_SCRIPT_START}\n/* AJT Japanese JS 5.6.7.8 */\n{EDIT_WARN}\nconsole.log('hi');\n{JS_SCRIPT_END}"
    )


def test_inline_bundled_css_strips_comments() -> None:
    """Verify inline_bundled_css() strips CSS comments from the code body."""
    vf = VersionedFile(
        version=FileVersionTuple(1, 0, 0, 0),
        text_content="/* AJT Japanese CSS 1.0.0.0 */\n/* a comment */\nbody { color: red; }\n",
    )
    result = inline_bundled_css(vf)
    # The wrapper adds its own comments (START, version, EDIT_WARN, END),
    # but the CSS code body between them should have no leftover comments.
    lines = result.split("\n")
    # Lines: START, version, EDIT_WARN, css_code, END
    assert len(lines) == 5
    css_code_line = lines[3]
    assert "/* a comment */" not in css_code_line
    assert "color: red" in css_code_line


def test_inline_bundled_js_strips_comments() -> None:
    """Verify inline_bundled_js() strips JS comments from the code body."""
    vf = VersionedFile(
        version=FileVersionTuple(1, 0, 0, 0),
        text_content="/* AJT Japanese JS 1.0.0.0 */\n// a line comment\nfunction foo() {}\n",
    )
    result = inline_bundled_js(vf)
    lines = result.split("\n")
    assert len(lines) == 5
    js_code_line = lines[3]
    assert "// a line comment" not in js_code_line
    assert "function foo()" in js_code_line


def test_css_add_idempotent() -> None:
    """Calling ensure_css_imports(add) twice should be idempotent after the first call."""
    model: AnkiNoteTypeDict = {"css": "/* user css */", "name": "pytest", "tmpls": [], "flds": []}
    assert ensure_css_imports(model, action=ChangeImportsAction.add) is True
    first_css = model["css"]
    assert ensure_css_imports(model, action=ChangeImportsAction.add) is False
    assert model["css"] == first_css


def test_js_add_idempotent() -> None:
    """Calling ensure_js_imports(add) twice should be idempotent after the first call."""
    side: AnkiCardSide = "qfmt"
    template: AnkiCardTemplateDict = {side: "<!-- template -->", "name": "pytest"}
    assert ensure_js_imports(template, side, action=ChangeImportsAction.add) is True
    first_html = template[side]
    assert ensure_js_imports(template, side, action=ChangeImportsAction.add) is False
    assert template[side] == first_html


def test_css_newer_inline_version_preserved() -> None:
    """A newer inline CSS block (not legacy @import) should be preserved, not downgraded."""
    newer_css = f"{CSS_START_TOKEN}\n/* AJT Japanese CSS 999.1.1.1 */\nsome newer css\n{CSS_END_TOKEN}"
    css_input = f"{CHARSET_RULE}\n{newer_css}\n/* user css */"
    model: AnkiNoteTypeDict = {"css": css_input, "name": "pytest", "tmpls": [], "flds": []}
    assert ensure_css_imports(model, action=ChangeImportsAction.add) is False
    assert model["css"] == css_input


def test_js_newer_inline_version_preserved() -> None:
    """A newer inline JS block should be preserved, not downgraded."""
    newer_js = f"{JS_SCRIPT_START}\n/* AJT Japanese JS 999.1.1.1 */\nsome newer js\n{JS_SCRIPT_END}"
    html_input = f"<!-- before -->\n{newer_js}\n<!-- after -->"
    side: AnkiCardSide = "qfmt"
    template: AnkiCardTemplateDict = {side: html_input, "name": "pytest"}
    assert ensure_js_imports(template, side, action=ChangeImportsAction.add) is False
    assert template[side] == html_input


@pytest.mark.parametrize(
    "inline_css, expected_version",
    [
        (
            f"{CSS_START_TOKEN}\n/* AJT Japanese CSS 1.2.3.4 */\nsome css\n{CSS_END_TOKEN}",
            FileVersionTuple(1, 2, 3, 4),
        ),
        (
            f"{CSS_START_TOKEN}\n/* AJT Japanese CSS 25.11.12.1 */\nsome css\n{CSS_END_TOKEN}",
            FileVersionTuple(25, 11, 12, 1),
        ),
    ],
)
def test_css_version_detection_from_inline_block(inline_css: str, expected_version: FileVersionTuple) -> None:
    """Verify CSSImportManager can detect versions from inline CSS blocks."""
    manager = CSSImportManager()
    imports = list(manager.find_code_imports(inline_css))
    assert len(imports) == 1
    assert imports[0].version == expected_version


@pytest.mark.parametrize(
    "inline_js, expected_version",
    [
        (
            f"{JS_SCRIPT_START}\n/* AJT Japanese JS 24.7.14.0 */\nsome js\n{JS_SCRIPT_END}",
            FileVersionTuple(24, 7, 14, 0),
        ),
        (
            f"{JS_SCRIPT_START}\n/* AJT Japanese JS 25.11.12.1 */\nsome js\n{JS_SCRIPT_END}",
            FileVersionTuple(25, 11, 12, 1),
        ),
    ],
)
def test_js_version_detection_from_inline_block(inline_js: str, expected_version: FileVersionTuple) -> None:
    """Verify JSImportManager can detect versions from inline JS blocks."""
    manager = JSImportManager()
    imports = list(manager.find_code_imports(inline_js))
    assert len(imports) == 1
    assert imports[0].version == expected_version


def test_css_remove_then_add_round_trip() -> None:
    """Removing CSS and then adding it should produce the same result as just adding."""
    css_input = f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* user css */"
    model: AnkiNoteTypeDict = {"css": css_input, "name": "pytest", "tmpls": [], "flds": []}
    ensure_css_imports(model, action=ChangeImportsAction.remove)
    assert BUNDLED_CSS_FILE.import_str not in model["css"]
    assert model["css"] == f"{CHARSET_RULE}\n/* user css */"
    ensure_css_imports(model, action=ChangeImportsAction.add)
    assert BUNDLED_CSS_FILE.import_str in model["css"]
    assert model["css"].startswith(CHARSET_RULE)
    assert model["css"] == f"{CHARSET_RULE}\n/* user css */\n{BUNDLED_CSS_FILE.import_str}"
