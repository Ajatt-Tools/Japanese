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
from japanese.note_type.imports import (
    ensure_css_imported,
    ensure_js_imported,
    find_existing_css_version,
)

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_name() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            """@import url("_file.css");\nbody { color: pink; }""",
            None,
        ),
        (
            """@import url("_file.css");\n@import url("_ajt_japanese.css");\nbody { color: pink; }""",
            UNK_VERSION,
        ),
        (
            """@import url("_file.css");\n@import url("_ajt_japanese_1.1.1.1.css");\nbody { color: pink; }""",
            (1, 1, 1, 1),
        ),
        (
            """@import url("_file.css");\n@import url("_ajt_japanese_12.12.12.12.css");\nbody { color: pink; }""",
            (12, 12, 12, 12),
        ),
    ],
)
def test_find_existing_css_version(test_input: str, expected: Optional[FileVersionTuple]) -> None:
    assert find_existing_css_version(test_input) == expected


def test_css_imports() -> None:
    # Import is missing.
    model_dict = {"css": "/* NO CSS */"}
    assert ensure_css_imported(model_dict) is True
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* NO CSS */"

    # Legacy import found.
    model_dict = {"css": f'@import url("_ajt_japanese.css");\n/* Other CSS */'}
    assert ensure_css_imported(model_dict) is True
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* Other CSS */"

    # Older version
    model_dict = {"css": f'/* Other CSS */\n@import url("_ajt_japanese_1.1.1.1.css");\n/* Other CSS */'}
    assert ensure_css_imported(model_dict) is True
    assert model_dict["css"] == f"/* Other CSS */\n{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */"

    # Current version
    model_dict = {"css": f"{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */"}
    assert ensure_css_imported(model_dict) is False
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* Other CSS */"

    # Newer version
    has_newer_import = f'/* Other CSS */\n@import url("_ajt_japanese_999.1.1.1.css");\n/* Other CSS */'
    model_dict = {"css": has_newer_import}
    assert ensure_css_imported(model_dict) is False
    assert model_dict["css"] == has_newer_import


def test_js_imports() -> None:
    side = "qfmt"

    # Import is missing.
    template_dict = {side: "<!-- empty template -->"}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == "<!-- empty template -->\n" + BUNDLED_JS_FILE.import_str

    # Legacy import found.
    has_legacy_import = '<!-- begin -->\n<script defer src="_ajt_japanese_24.7.14.2.js"></script>\n<!-- end -->'
    template_dict = {side: has_legacy_import}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}"

    # Older version
    template_dict = {side: "<script>\n/* AJT Japanese JS 24.7.14.0 */\n//some old code\n</script>\n<!--whatever-->"}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == BUNDLED_JS_FILE.import_str + "\n<!--whatever-->"

    # Current version
    up_to_date_template = f"<!-- template text -->\n{BUNDLED_JS_FILE.import_str}\n<!-- template text -->"
    template_dict = {side: up_to_date_template}
    assert ensure_js_imported(template_dict, side) is False
    assert template_dict[side] == up_to_date_template

    # Newer version
    newer_template = "<script>\n/* AJT Japanese JS 999.1.1.1 */\n//some new code\n</script>\n<!--whatever-->"
    template_dict = {side: newer_template}
    assert ensure_js_imported(template_dict, side) is False
    assert template_dict[side] == newer_template
