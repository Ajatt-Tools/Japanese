# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import gui_hooks

from .config_view import get_global_config
from .furigana.gen_furigana import get_global_furigana_generator
from .pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from .pitch_accents.accent_lookup import get_global_accent_lookup, get_global_mecab

# Entry point for Anki.
# This module creates the global objects used by the rest of the add-on.
# It can only be imported when Anki is running.
# Entry formatting functions live in pitch_accents/format_entries.py (see EntryFormatter).


# Entry point
##########################################################################

cfg = get_global_config()
mecab = get_global_mecab()
lookup = get_global_accent_lookup()
acc_dict = AccentDictManager2()
gui_hooks.main_window_did_init.append(acc_dict.ensure_dict_ready)
fgen = get_global_furigana_generator()
