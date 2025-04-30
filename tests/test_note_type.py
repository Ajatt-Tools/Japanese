# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re
from typing import Optional

import pytest

from japanese.note_type.bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    UNK_VERSION,
    FileVersionTuple,
)
from japanese.note_type.files_in_col_media import FileInCollection
from japanese.note_type.imports import (
    CHARSET_RULE,
    ensure_css_imported,
    ensure_js_imported,
    find_existing_css_version,
)
from japanese.note_type.typing import AnkiNoteTypeDict

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_name() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


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
    "css_styling, is_modified, modified_css",
    [
        (
            # Import is missing.
            """/* NO CSS */""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* NO CSS */",
        ),
        (
            # Charset is declared.
            f"""{CHARSET_RULE}\n/*Other CSS*/""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/*Other CSS*/",
        ),
        (
            # Legacy import found.
            """@import url("_ajt_japanese.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */",
        ),
        (
            # Older version
            """/* Other CSS */\n@import url("_ajt_japanese_1.1.1.1.css");\n/* Other CSS */""",
            True,
            f"{CHARSET_RULE}\n/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */",
        ),
        (
            # Current version
            f"{CHARSET_RULE}\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */\n/* Other CSS */\n",
            False,
            None,
        ),
        (
            # Newer version
            f"""{CHARSET_RULE}\n/* Other CSS */\n@import url("_ajt_japanese_999.1.1.1.css");\n/* Other CSS */""",
            False,
            None,
        ),
    ],
)
def test_css_imports(css_styling: str, is_modified: bool, modified_css: Optional[str]) -> None:
    model_dict: AnkiNoteTypeDict = {"css": css_styling, "name": "pytest", "tmpls": []}
    assert ensure_css_imported(model_dict) is is_modified
    assert model_dict["css"] == (modified_css or css_styling)


@pytest.mark.parametrize(
    "template_html, is_modified, modified_html",
    [
        (
            # Import is missing.
            """<!-- empty template -->""",
            True,
            f"<!-- empty template -->\n{BUNDLED_JS_FILE.import_str}",
        ),
        (
            # Legacy import found.
            """<!-- begin -->\n<script defer src="_ajt_japanese_24.7.14.2.js"></script>\n<!-- end -->""",
            True,
            f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}",
        ),
        (
            # Legacy import found.
            """<!-- begin -->\n<script src="_ajt_japanese.js"></script>\n<!-- end -->""",
            True,
            f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}",
        ),
        (
            # Older version
            "<script>\n/* AJT Japanese JS 24.7.14.0 */\n//some old code\n</script>\n<!--whatever-->",
            True,
            f"{BUNDLED_JS_FILE.import_str}\n<!--whatever-->",
        ),
        (
            # Older version (but it is formatted)
            (
                "<!--whatever-->\n\n"
                "<script>\n"
                "    /* AJT Japanese JS 24.7.14.0 */\n"
                "    //some old code\n"
                "</script>\n"
                "<!--whatever-->"
            ),
            True,
            f"<!--whatever-->\n\n{BUNDLED_JS_FILE.import_str}\n<!--whatever-->",
        ),
        (
            # Current version
            f"<!-- template text -->\n{BUNDLED_JS_FILE.import_str}\n<!-- template text -->",
            False,
            None,
        ),
        (
            # Newer version
            "<script>\n/* AJT Japanese JS 999.1.1.1 */\n//some new code\n</script>\n<!--whatever-->",
            False,
            None,
        ),
    ],
)
def test_js_imports(template_html: str, is_modified: bool, modified_html: Optional[str]) -> None:
    side = "qfmt"
    template_dict = {side: template_html, "name": "pytest"}
    assert ensure_js_imported(template_dict, side) is is_modified
    assert template_dict[side] == (modified_html or template_html)


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
