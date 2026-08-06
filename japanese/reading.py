# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from aqt import gui_hooks

from .config_view import get_global_config
from .database.sqlite3_buddy import Sqlite3Buddy
from .furigana.gen_furigana import get_global_furigana_generator
from .helpers.profiles import ColorCodePitchFormat
from .pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from .pitch_accents.accent_lookup import get_global_accent_lookup, get_global_mecab

# Entry point for Anki.
# This module creates the global objects used by the rest of the add-on.
# It can only be imported when Anki is running.
# Entry formatting functions live in pitch_accents/format_entries.py (see EntryFormatter).


def generate_furigana(
    src_text: str,
    *,
    split_morphemes: bool = True,
    full_hiragana: bool = False,
    output_format: ColorCodePitchFormat = ColorCodePitchFormat(0),
    accent_db_path: pathlib.Path | None = None,
) -> str:
    """Generate furigana for the source text using a temporary db connection."""
    with Sqlite3Buddy(accent_db_path) as db:
        return fgen.with_new_buddy(db).generate_furigana(
            src_text,
            split_morphemes=split_morphemes,
            full_hiragana=full_hiragana,
            output_format=output_format,
        )


# Entry point
##########################################################################

cfg = get_global_config()
mecab = get_global_mecab()
lookup = get_global_accent_lookup()
acc_dict = AccentDictManager2()
gui_hooks.main_window_did_init.append(acc_dict.ensure_dict_ready)
fgen = get_global_furigana_generator()
