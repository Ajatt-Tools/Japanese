# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections import OrderedDict
from collections.abc import Sequence
from typing import Optional, TypeVar

from aqt import gui_hooks

from .config_view import config_view as cfg
from .furigana.gen_furigana import FuriganaGen, discard_extra_readings
from .helpers.profiles import PitchOutputFormat
from .mecab_controller.kana_conv import to_hiragana
from .mecab_controller.mecab_controller import MecabController
from .pitch_accents.acc_dict_mgr import AccentDict, AccentDictManager, FormattedEntry
from .pitch_accents.accent_lookup import AccentLookup
from .pitch_accents.styles import STYLE_MAP
from .pitch_accents.svg_graphs import SvgPitchGraphMaker

# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """Map style classes to their user-configured inline versions."""
    for k, v in STYLE_MAP[cfg.pitch_accent.html_style].items():
        txt = txt.replace(k, v)
    return txt


def update_html(html_notation: str) -> str:
    html_notation = convert_to_inline_style(html_notation)
    if cfg.pitch_accent.output_hiragana:
        html_notation = to_hiragana(html_notation)
    return html_notation


def get_notation(entry: FormattedEntry, mode: PitchOutputFormat) -> str:
    if mode == PitchOutputFormat.html:
        return update_html(entry.html_notation)
    elif mode == PitchOutputFormat.number:
        return entry.pitch_number
    elif mode == PitchOutputFormat.html_and_number:
        return update_html(f"{entry.html_notation} {entry.pitch_number_html}")
    elif mode == PitchOutputFormat.svg:
        return svg_graph_maker.make_graph(entry)
    raise RuntimeError("Unreachable.")


def sort_entries(entries: Sequence[FormattedEntry]) -> Sequence[FormattedEntry]:
    return sorted(entries, key=lambda entry: (entry.katakana_reading, entry.pitch_number))


def entries_to_html(
    entries: Sequence[FormattedEntry],
    output_format: PitchOutputFormat,
    max_results: Optional[int],
) -> Sequence[str]:
    """
    Convert entries to HTML, sort and remove duplicates.
    """
    return discard_extra_readings(
        tuple(dict.fromkeys(get_notation(entry, output_format) for entry in sort_entries(entries))),
        max_results=max_results or cfg.pitch_accent.maximum_results,
        discard_mode=cfg.pitch_accent.discard_mode,
    )


def format_pronunciations(
    pronunciations: AccentDict,
    output_format: PitchOutputFormat = PitchOutputFormat.html,
    sep_single: str = "・",
    sep_multi: str = "、",
    expr_sep: Optional[str] = None,
    max_results: Optional[int] = None,
) -> str:
    ordered_dict = OrderedDict()
    for word, entries in pronunciations.items():
        if entries_html := entries_to_html(entries, output_format, max_results=max_results):
            ordered_dict[word] = sep_single.join(entries_html)

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join(f"{word}{expr_sep}{entries}" for word, entries in ordered_dict.items() if word and entries)
    else:
        txt = sep_multi.join(ordered_dict.values())

    return txt


# Entry point
##########################################################################

mecab = MecabController(verbose=True, cache_max_size=cfg.cache_lookups)
svg_graph_maker = SvgPitchGraphMaker(options=cfg.svg_graphs)
acc_dict = AccentDictManager()
lookup = AccentLookup(acc_dict, cfg, mecab)
gui_hooks.main_window_did_init.append(acc_dict.reload_from_disk)
fgen = FuriganaGen(cfg, mecab, lookup)
