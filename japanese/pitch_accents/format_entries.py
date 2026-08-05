# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Formatting helpers for pitch accent entries.
# EntryFormatter receives config and SVG adapter dependencies explicitly, so
# reading.py keeps only the Anki entry point globals and generate_furigana().

from collections import OrderedDict
from collections.abc import Sequence

from ..config_view import JapaneseConfig
from ..helpers.misc import compact_seq
from ..helpers.profiles import PitchOutputFormat
from ..mecab_controller.kana_conv import to_hiragana
from .basic_types import count_moras, pitch_type_from_pitch_num
from .common import AccentDict, FormattedEntry
from .entry_to_svg import FormattedEntryToSvgAdapter
from .pitch_to_json import MoraSequenceOutputJson, make_json_from_entry
from .styles import (
    PITCH_COLOR_PLACEHOLDER,
    STYLE_MAP,
    HTMLPitchPatternStyle,
)


def convert_to_inline_style(txt: str, pitch_color: str, pitch_accent_style: HTMLPitchPatternStyle) -> str:
    """Map style classes to their user-configured inline versions."""
    if not pitch_color:
        pitch_color = "currentColor"  # fallback
    for k, v in STYLE_MAP[pitch_accent_style].items():
        txt = txt.replace(k, v)
    txt = txt.replace(PITCH_COLOR_PLACEHOLDER, pitch_color)
    return txt


def sort_entries(entries: Sequence[FormattedEntry]) -> Sequence[FormattedEntry]:
    """Sort entries by katakana reading, then by pitch number."""
    return sorted(entries, key=lambda entry: (entry.katakana_reading, entry.pitch_number))


class EntryFormatter:
    """Format pitch accent entries as styled HTML, pitch numbers, or SVG graphs."""

    _cfg: JapaneseConfig
    _svg_maker: FormattedEntryToSvgAdapter

    def __init__(self, cfg: JapaneseConfig, *, svg_maker: FormattedEntryToSvgAdapter | None = None) -> None:
        """Initialize the formatter, reusing the injected SVG adapter if one is provided."""
        self._cfg = cfg
        self._svg_maker = svg_maker or FormattedEntryToSvgAdapter(cfg)

    def _pitch_color_from_entry(self, entry: FormattedEntry) -> str:
        """Look up the user-configured pitch color for the entry's accent type."""
        return self._cfg.pitch_color_codes.lookup_color(
            pitch_type_from_pitch_num(entry.pitch_number, count_moras(entry.katakana_reading))
        )

    def update_html(self, entry: FormattedEntry, pitch_accent_style: HTMLPitchPatternStyle) -> str:
        """Convert the entry's HTML notation to the requested inline style."""
        html_notation = convert_to_inline_style(
            entry.html_notation,
            pitch_color=self._pitch_color_from_entry(entry),
            pitch_accent_style=pitch_accent_style,
        )
        if self._cfg.pitch_accent.output_hiragana:
            html_notation = to_hiragana(html_notation)
        return html_notation

    def _get_notation(self, entry: FormattedEntry, mode: PitchOutputFormat) -> str:
        """Format a single entry as HTML, a pitch number, or an SVG graph."""
        match mode:
            case PitchOutputFormat.html:
                return self.update_html(entry, pitch_accent_style=self._cfg.pitch_accent.html_style)
            case PitchOutputFormat.number:
                return entry.pitch_number
            case PitchOutputFormat.html_and_number:
                return (
                    f"{self.update_html(entry, pitch_accent_style=self._cfg.pitch_accent.html_style)}"
                    f" {entry.pitch_number_html}"
                )
            case PitchOutputFormat.svg:
                return self._svg_maker.make_graph(entry)
        raise RuntimeError(f"Unsupported output format: {mode.name}")

    def _entries_to_html(
        self,
        entries: Sequence[FormattedEntry],
        output_format: PitchOutputFormat,
        max_results: int,
    ) -> Sequence[str]:
        """Convert entries to HTML, sort and remove duplicates."""
        return compact_seq(self._get_notation(entry, output_format) for entry in sort_entries(entries))[:max_results]

    def pronunciations_to_json(
        self, pronunciations: AccentDict, *, max_results: int
    ) -> Sequence[MoraSequenceOutputJson]:
        """Convert pronunciations to a list of JSON-serializable mora sequences."""
        result: dict[str, MoraSequenceOutputJson] = OrderedDict()
        for word, entries in pronunciations.items():
            for entry in sort_entries(entries):
                result[self.update_html(entry, pitch_accent_style=self._cfg.pitch_accent.html_style)] = (
                    make_json_from_entry(entry)
                )
        return tuple(result.values())[:max_results]

    def format_pronunciations(
        self,
        pronunciations: AccentDict,
        *,
        output_format: PitchOutputFormat = PitchOutputFormat.html,
        max_results: int,
        sep_single: str = "・",
        sep_multi: str = "、",
        expr_sep: str | None = None,
    ) -> str:
        """Format pronunciations as a single string of styled pitch accent entries."""
        ordered_dict: dict[str, str] = OrderedDict()
        for word, entries in pronunciations.items():
            if entries_html := self._entries_to_html(entries, output_format, max_results):
                ordered_dict[word] = sep_single.join(entries_html)

        # expr_sep is used to separate entries on lookup
        if expr_sep:
            txt = sep_multi.join(
                f"{word}{expr_sep}{entries}" for word, entries in ordered_dict.items() if word and entries
            )
        else:
            txt = sep_multi.join(ordered_dict.values())

        return txt
