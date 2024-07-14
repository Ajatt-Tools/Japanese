# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re

from japanese.note_type.bundled_files import BUNDLED_CSS_FILE, BUNDLED_JS_FILE
from japanese.note_type.imports import ensure_css_imported, ensure_js_imported

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_name() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


def test_css_imports() -> None:
    model_dict = {"css": "/* NO CSS */"}
    assert ensure_css_imported(model_dict) is True
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* NO CSS */"

    model_dict = {"css": f'@import url("_ajt_japanese.css");\n/* Other CSS */'}
    assert ensure_css_imported(model_dict) is True
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* Other CSS */"

    model_dict = {"css": f"{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */"}
    assert ensure_css_imported(model_dict) is False
    assert model_dict["css"] == BUNDLED_CSS_FILE.import_str + "\n/* Other CSS */"


def test_js_imports() -> None:
    side = "qfmt"
    template_dict = {side: "<!-- empty template -->"}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == "<!-- empty template -->\n" + BUNDLED_JS_FILE.import_str

    up_to_date_template = f"<!-- template text -->\n{BUNDLED_JS_FILE.import_str}\n<!-- template text -->"
    template_dict = {side: up_to_date_template}
    assert ensure_js_imported(template_dict, side) is False
    assert template_dict[side] == up_to_date_template

    template_dict = {side: "<script>\n/* AJT Japanese JS 24.7.14.0 */\n//some old code\n</script>\n<!--whatever-->"}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == BUNDLED_JS_FILE.import_str + "\n<!--whatever-->"

    has_legacy_import = '<!-- begin -->\n<script defer src="_ajt_japanese_24.7.14.2.js"></script>\n<!-- end -->'
    template_dict = {side: has_legacy_import}
    assert ensure_js_imported(template_dict, side) is True
    assert template_dict[side] == f"<!-- begin -->\n<!-- end -->\n{BUNDLED_JS_FILE.import_str}"
