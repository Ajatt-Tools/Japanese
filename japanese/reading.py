# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections import OrderedDict
from collections.abc import Sequence
from typing import Optional

from aqt import gui_hooks

from .config_view import config_view as cfg
from .database.sqlite3_buddy import Sqlite3Buddy
from .furigana.gen_furigana import FuriganaGen
from .helpers.profiles import ColorCodePitchFormat, PitchOutputFormat
from .mecab_controller.kana_conv import to_hiragana
from .mecab_controller.mecab_controller import MecabController
from .pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from .pitch_accents.accent_lookup import AccentLookup
from .pitch_accents.basic_types import (
    PitchColor,
    count_moras,
    pitch_type_from_pitch_num,
)
from .pitch_accents.common import AccentDict, FormattedEntry
from .pitch_accents.styles import (
    PITCH_COLOR_PLACEHOLDER,
    STYLE_MAP,
    HTMLPitchPatternStyle,
)
from .pitch_accents.svg_graphs import SvgPitchGraphMaker

# Lookup
##########################################################################


def convert_to_inline_style(txt: str, pitch_color: str, pitch_accent_style: HTMLPitchPatternStyle) -> str:
    """Map style classes to their user-configured inline versions."""
    for k, v in STYLE_MAP[pitch_accent_style].items():
        txt = txt.replace(k, v)
    txt = txt.replace(PITCH_COLOR_PLACEHOLDER, pitch_color)
    return txt


def pitch_color_from_entry(entry: FormattedEntry) -> str:
    pitch_type = pitch_type_from_pitch_num(entry.pitch_number, count_moras(entry.katakana_reading))
    try:
        return PitchColor[pitch_type.name].value
    except KeyError:
        return PitchColor.unknown.value


def update_html(entry: FormattedEntry, pitch_accent_style: HTMLPitchPatternStyle) -> str:
    html_notation = convert_to_inline_style(
        entry.html_notation,
        pitch_color=pitch_color_from_entry(entry),
        pitch_accent_style=pitch_accent_style,
    )
    if cfg.pitch_accent.output_hiragana:
        html_notation = to_hiragana(html_notation)
    return html_notation


def get_notation(entry: FormattedEntry, mode: PitchOutputFormat) -> str:
    if mode == PitchOutputFormat.html:
        return update_html(entry, pitch_accent_style=cfg.pitch_accent.html_style)
    elif mode == PitchOutputFormat.number:
        return entry.pitch_number
    elif mode == PitchOutputFormat.html_and_number:
        return f"{update_html(entry, pitch_accent_style=cfg.pitch_accent.html_style)} {entry.pitch_number_html}"
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
    readings = tuple(dict.fromkeys(get_notation(entry, output_format) for entry in sort_entries(entries)))
    max_results = max_results or cfg.pitch_accent.maximum_results
    return readings[:max_results]


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


def generate_furigana(
    src_text: str,
    *,
    split_morphemes: bool = True,
    full_hiragana: bool = False,
    output_format: ColorCodePitchFormat = ColorCodePitchFormat(0),
) -> str:
    with Sqlite3Buddy() as db:
        return fgen.with_new_buddy(db).generate_furigana(
            src_text,
            split_morphemes=split_morphemes,
            full_hiragana=full_hiragana,
            output_format=output_format,
        )


# Entry point
##########################################################################

mecab = MecabController(verbose=True, cache_max_size=cfg.cache_lookups)
svg_graph_maker = SvgPitchGraphMaker(options=cfg.svg_graphs)
acc_dict = AccentDictManager2()
lookup = AccentLookup(cfg, mecab)
gui_hooks.main_window_did_init.append(acc_dict.ensure_dict_ready)
fgen = FuriganaGen(cfg, lookup, mecab)
