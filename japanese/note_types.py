# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import glob
import os.path
from collections.abc import Sequence

import anki.collection
from anki.models import NotetypeNameId
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp

from .config_view import config_view as cfg
from .helpers.consts import ADDON_NAME
from .note_type.bundled_files import (
    BUNDLED_CSS_FILE,
    BUNDLED_JS_FILE,
    BundledNoteTypeSupportFile,
    get_file_version,
)
from .note_type.imports import ensure_js_imported, ensure_css_imported


def not_recent_version(file: BundledNoteTypeSupportFile) -> bool:
    return get_file_version(file.file_path) > get_file_version(file.path_in_col())


def save_to_col(file: BundledNoteTypeSupportFile) -> None:
    with open(file.file_path, encoding="utf-8") as in_f, open(file.path_in_col(), "w", encoding="utf-8") as out_f:
        out_f.write(in_f.read())


def is_debug_enabled() -> bool:
    return "QTWEBENGINE_REMOTE_DEBUGGING" in os.environ


def ensure_files_saved():
    for file in (BUNDLED_JS_FILE, BUNDLED_CSS_FILE):
        if not_recent_version(file) or is_debug_enabled():
            save_to_col(file)
            print(f"Created new file: {file.name_in_col}")


def collect_all_relevant_models() -> Sequence[NotetypeNameId]:
    assert mw
    return [
        model
        for model in mw.col.models.all_names_and_ids()
        if any(
            profile.note_type.lower() in model.name.lower()
            for profile in cfg.iter_profiles()
            if profile.mode == "furigana"
        )
    ]


def ensure_imports_added_for_model(col: anki.collection.Collection, model: NotetypeNameId) -> bool:
    model_dict = col.models.get(model.id)
    if not model_dict:
        return False
    is_dirty = ensure_css_imported(model_dict)
    for template in model_dict["tmpls"]:
        for side in ("qfmt", "afmt"):
            is_dirty = ensure_js_imported(template, side) or is_dirty
    if is_dirty:
        col.models.update_dict(model_dict)
        print(f"Model {model.name} is dirty.")
    return is_dirty


def ensure_imports_added_op(col: anki.collection.Collection) -> anki.collection.OpChanges:
    assert mw
    models = collect_all_relevant_models()
    pos = col.add_custom_undo_entry(f"{ADDON_NAME}: Add imports to {len(models)} models.")
    is_dirty = False
    for model in models:
        print(f"Relevant AJT note type: {model.name}")
        is_dirty = ensure_imports_added_for_model(col, model) or is_dirty
    return col.merge_undo_entries(pos) if is_dirty else anki.collection.OpChanges()


def ensure_imports_added() -> None:
    assert mw
    CollectionOp(mw, lambda col: ensure_imports_added_op(col)).success(lambda _: None).run_in_background()


def remove_old_versions() -> None:
    assert mw
    all_ajt_file_names = frozenset(glob.glob("_ajt_japanese*.*", root_dir=mw.col.media.dir()))
    current_ajt_file_names = frozenset((BUNDLED_JS_FILE.name_in_col, BUNDLED_CSS_FILE.name_in_col))
    for old_file_name in all_ajt_file_names - current_ajt_file_names:
        os.unlink(os.path.join(mw.col.media.dir(), old_file_name))
        print(f"Removed old version: {old_file_name}")


def prepare_note_types() -> None:
    assert mw
    ensure_files_saved()
    ensure_imports_added()
    remove_old_versions()


def init():
    gui_hooks.profile_did_open.append(prepare_note_types)
