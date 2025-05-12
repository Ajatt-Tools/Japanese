# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
import typing
from collections.abc import Sequence
from typing import Optional

import anki.collection
from anki.hooks import wrap
from anki.models import NotetypeNameId
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp

from ..ajt_common.model_utils import AnkiNoteTypeDict, get_model_field_names
from ..config_view import config_view as cfg
from ..helpers.consts import ADDON_NAME
from ..helpers.profiles import ProfileFurigana
from ..tasks import note_type_matches
from .bundled_files import BUNDLED_CSS_FILE, BundledCSSFile, get_file_version
from .files_in_col_media import FileInCollection, find_ajt_scripts_in_collection
from .imports import ensure_css_imported, ensure_js_imported


def not_recent_version(file: BundledCSSFile) -> bool:
    return file.version > get_file_version(file.path_in_col()).version


def save_to_col(file: BundledCSSFile) -> None:
    with open(file.path_in_col(), "w", encoding="utf-8") as of:
        of.write(file.text_content)


def is_debug_enabled() -> bool:
    return "QTWEBENGINE_REMOTE_DEBUGGING" in os.environ


def ensure_bundled_css_file_saved() -> None:
    """
    Save the AJT Japanese CSS file to the 'collection.media' folder.
    """
    if not_recent_version(BUNDLED_CSS_FILE) or is_debug_enabled():
        save_to_col(BUNDLED_CSS_FILE)
        print(f"Created new file: {BUNDLED_CSS_FILE.name_in_col}")


def field_names_from_model_dict(model_dict: AnkiNoteTypeDict) -> frozenset[str]:
    """
    Return all field names in the provided note type, e.g. ["VocabKanji", "SentKanji", "VocabDef"].
    """
    return frozenset(get_model_field_names(model_dict))


def is_relevant_model(model_dict: Optional[AnkiNoteTypeDict]) -> bool:
    assert model_dict, "model dict must not be None"
    all_field_names = field_names_from_model_dict(model_dict)
    return any(
        note_type_matches(model_dict, profile) and profile.source in all_field_names
        for profile in cfg.iter_profiles()
        if isinstance(profile, ProfileFurigana)
    )


def collect_all_relevant_models() -> Sequence[NotetypeNameId]:
    """
    Find all note types (models) that require additional JS+CSS imports
    to enable the display of pitch accent information on mouse hover.
    """
    assert mw
    return [model for model in mw.col.models.all_names_and_ids() if is_relevant_model(mw.col.models.get(model.id))]


def ensure_imports_in_model_dict(model_dict: AnkiNoteTypeDict) -> bool:
    if not model_dict:
        return False
    is_dirty = ensure_css_imported(model_dict)
    for template in model_dict["tmpls"]:
        side: typing.Literal["qfmt", "afmt"]
        for side in ("qfmt", "afmt"):
            is_dirty = ensure_js_imported(template, side) or is_dirty
    if is_dirty:
        print(f"Model {model_dict['name']} is dirty.")
    return is_dirty


def ensure_imports_and_save_model(col: anki.collection.Collection, model_dict: AnkiNoteTypeDict) -> bool:
    if is_dirty := ensure_imports_in_model_dict(model_dict):
        col.models.update_dict(model_dict)
    return is_dirty


def ensure_imports_added_op(
    col: anki.collection.Collection, models: Sequence[NotetypeNameId]
) -> anki.collection.OpChanges:
    assert mw
    pos = col.add_custom_undo_entry(f"{ADDON_NAME}: Add imports to {len(models)} models.")
    is_dirty = False
    for model in models:
        print(f"Relevant AJT note type: {model.name}")
        is_dirty = ensure_imports_and_save_model(col, col.models.get(model.id)) or is_dirty
    return col.merge_undo_entries(pos) if is_dirty else anki.collection.OpChanges()


def ensure_imports_added(models: Sequence[NotetypeNameId]) -> None:
    assert mw
    CollectionOp(mw, lambda col: ensure_imports_added_op(col, models)).success(lambda _: None).run_in_background()


def remove_old_file_versions() -> None:
    assert mw
    saved_files: frozenset[FileInCollection] = find_ajt_scripts_in_collection() - {BUNDLED_CSS_FILE.name_in_col}
    for file in saved_files:
        if file.version < BUNDLED_CSS_FILE.version:
            os.unlink(os.path.join(mw.col.media.dir(), file.name))
            print(f"Removed old version: {file.name}")


def on_model_updated(notetype: AnkiNoteTypeDict, skip_checks: bool = False) -> None:
    # When gomi updates a note type (using AnkiConnect),
    # it removes AJT Japanese's code (JS and CSS imports) to avoid redundancy.
    # Now AJT Japanese needs to add the code back to avoid breakage.
    # Reference: https://github.com/Ajatt-Tools/gomi
    assert isinstance(notetype, dict), "note type should be a dictionary."
    ensure_imports_in_model_dict(notetype)


def prepare_note_types() -> None:
    if not cfg.insert_scripts_into_templates:
        # Global switch (in Advanced settings, not shown in the GUI settings.)
        return
    if models := collect_all_relevant_models():
        # Add scripts to templates only if the user has profiles (tasks) where furigana needs to be generated.
        ensure_bundled_css_file_saved()
        ensure_imports_added(models)
        remove_old_file_versions()

    # AnkiConnect calls mw.col.models.update_dict()
    # when the "updateModelTemplates" and "updateModelStyling" actions are used.
    mw.col.models.update_dict = wrap(mw.col.models.update_dict, on_model_updated, "before")


def init() -> None:
    gui_hooks.profile_did_open.append(prepare_note_types)
