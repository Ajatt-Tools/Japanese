# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
import re
from collections.abc import Sequence

import anki.collection
from anki.models import NotetypeNameId
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp

from .config_view import config_view as cfg
from .helpers import ADDON_NAME
from .note_type.consts import AJT_JAPANESE_CSS_PATH, AJT_JAPANESE_JS_PATH

RE_VERSION_STR = re.compile(r"AJT Japanese (?P<type>JS|CSS) (?P<version>\d+\.\d+\.\d+\.\d+)")
FileVersion = tuple[int, int, int, int]
UNK_VERSION = 0, 0, 0, 0


def parse_version_str(file_content: str):
    m = re.search(RE_VERSION_STR, file_content)
    if not m:
        return UNK_VERSION
    return tuple(int(value) for value in m.group("version").split("."))


def get_file_version(file_path) -> FileVersion:
    try:
        with open(file_path, encoding="utf-8") as rf:
            return parse_version_str(rf.read())
    except FileNotFoundError:
        pass
    return UNK_VERSION


def not_recent_version(file_path: str) -> bool:
    assert mw
    path_in_col = os.path.join(mw.col.media.dir(), os.path.basename(file_path))
    return get_file_version(file_path) > get_file_version(path_in_col)


def save_to_col(file_path: str) -> None:
    assert mw
    path_in_col = os.path.join(mw.col.media.dir(), os.path.basename(file_path))
    with open(path_in_col, "w", encoding="utf-8") as of, open(file_path, encoding="utf-8") as rf:
        of.write(rf.read())


def is_debug_enabled() -> bool:
    return "QTWEBENGINE_REMOTE_DEBUGGING" in os.environ


def ensure_files_saved():
    for file_path in (AJT_JAPANESE_JS_PATH, AJT_JAPANESE_CSS_PATH):
        if not_recent_version(file_path) or is_debug_enabled():
            print(f"AJT file needs updating: {os.path.basename(file_path)}")
            save_to_col(file_path)


AJT_CSS_IMPORT = f'@import url("{os.path.basename(AJT_JAPANESE_CSS_PATH)}");'
AJT_JS_IMPORT = f'<script defer src="{os.path.basename(AJT_JAPANESE_JS_PATH)}"></script>'


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
    is_dirty = False
    if AJT_CSS_IMPORT not in model_dict["css"]:
        model_dict["css"] = f'{AJT_CSS_IMPORT}\n{model_dict["css"]}'
        is_dirty = True
    for template in model_dict["tmpls"]:
        for side in ("qfmt", "afmt"):
            if AJT_JS_IMPORT not in template[side]:
                template[side] = f"{template[side]}\n{AJT_JS_IMPORT}"
                is_dirty = True
    if is_dirty:
        col.models.update_dict(model_dict)
    return is_dirty


def ensure_imports_added(col: anki.collection.Collection):
    assert mw
    models = collect_all_relevant_models()
    pos = col.add_custom_undo_entry(f"{ADDON_NAME}: Add imports to {len(models)} models.")
    is_dirty = False
    for model in models:
        print(f"Relevant AJT note type: {model.name}")
        is_dirty = ensure_imports_added_for_model(col, model) or is_dirty
    return col.merge_undo_entries(pos) if is_dirty else anki.collection.OpChanges()


def prepare_note_types():
    ensure_files_saved()
    CollectionOp(
        mw,
        lambda col: ensure_imports_added(col),
    ).success(lambda _: None).run_in_background()


def init():
    gui_hooks.profile_did_open.append(prepare_note_types)
