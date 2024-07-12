# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import re

from japanese.note_type.bundled_files import BUNDLED_CSS_FILE, BUNDLED_JS_FILE
from japanese.note_type.imports import ensure_css_imported

RE_EXPECTED_FILENAME = re.compile(r"_ajt_japanese_(\d+\.){4}(js|css)")


def test_expected_file_names() -> None:
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_JS_FILE.name_in_col)
    assert re.fullmatch(RE_EXPECTED_FILENAME, BUNDLED_CSS_FILE.name_in_col)


def test_css_imports() -> None:
    model_dict = {"css": "/* NO CSS */"}
    assert ensure_css_imported(model_dict) is True

    model_dict = {"css": f'@import url("_ajt_japanese.css");\n/* Other CSS */'}
    assert ensure_css_imported(model_dict) is True

    model_dict = {"css": f"{BUNDLED_CSS_FILE.import_str}\n/* Other CSS */"}
    assert ensure_css_imported(model_dict) is False
