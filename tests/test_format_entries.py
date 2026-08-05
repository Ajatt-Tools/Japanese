# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import typing
from collections.abc import Sequence
from unittest.mock import create_autospec

import pytest

from japanese.helpers.profiles import PitchOutputFormat
from japanese.pitch_accents.common import AccentDict, FormattedEntry
from japanese.pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from japanese.pitch_accents.format_entries import (
    EntryFormatter,
    convert_to_inline_style,
    sort_entries,
)
from japanese.pitch_accents.pitch_to_json import MoraSequenceOutputJson
from japanese.pitch_accents.styles import HTMLPitchPatternStyle
from playground.utils import NoAnkiConfigView
from tests.helpers import make_fresh_config

HEIBAN_ENTRY: typing.Final = FormattedEntry("僕", "ボク", "<low_rise>ボ</low_rise><high>ク</high>", "0")
ATAMADAKA_ENTRY: typing.Final = FormattedEntry("僕", "ボク", "<high_drop>ボ</high_drop><low>ク</low>", "1")
GAKKOU_ENTRY: typing.Final = FormattedEntry("学校", "ガッコウ", "<low_rise>ガ</low_rise><high>ッコウ</high>", "0")

# Expected u_biq renderings (the default html_style in config.json).
HEIBAN_UBIQ: typing.Final = (
    '<span style="box-shadow: inset -2px -2px 0 0 #FF6633;">ボ</span>'
    '<span style="box-shadow: inset 0px 2px 0 0px #FF6633;">ク</span>'
)
ATAMADAKA_UBIQ: typing.Final = (
    '<span style="box-shadow: inset -2px 2px 0 0px #FF6633;">ボ</span>'
    '<span style="box-shadow: inset 0px -2px 0 0px #FF6633;">ク</span>'
)
GAKKOU_UBIQ: typing.Final = (
    '<span style="box-shadow: inset -2px -2px 0 0 #FF6633;">ガ</span>'
    '<span style="box-shadow: inset 0px 2px 0 0px #FF6633;">ッコウ</span>'
)


class TestConvertToInlineStyle:
    """Style tags are replaced with inline styles; the color placeholder is filled."""

    @pytest.mark.parametrize(
        "txt, pitch_color, pitch_accent_style, expected",
        [
            # javdejong: low tags are dropped, high gets an overline, color is unused.
            (
                "<low_rise>ボ</low_rise><high>ク</high>",
                "red",
                HTMLPitchPatternStyle.javdejong,
                'ボ<span style="text-decoration:overline;">ク</span>',
            ),
            # u_biq: the color is baked in (#FF6633); the passed color is ignored.
            (
                "<low_rise>ボ</low_rise><high>ク</high>",
                "red",
                HTMLPitchPatternStyle.u_biq,
                HEIBAN_UBIQ,
            ),
            # u_biq_color_coded: the placeholder is replaced with the passed color.
            (
                "<low_rise>ボ</low_rise>",
                "#123456",
                HTMLPitchPatternStyle.u_biq_color_coded,
                '<span style="box-shadow: inset -2px -2px 0 0 #123456;">ボ</span>',
            ),
            # Empty color falls back to currentColor.
            (
                "<low_rise>ボ</low_rise>",
                "",
                HTMLPitchPatternStyle.u_biq_color_coded,
                '<span style="box-shadow: inset -2px -2px 0 0 currentColor;">ボ</span>',
            ),
            (
                "<low_rise>ボ</low_rise><high>ク</high>",
                "red",
                HTMLPitchPatternStyle.none,
                '<span class="low_rise">ボ</span><span class="high">ク</span>',
            ),
            (
                "<high>ク</high>",
                "red",
                HTMLPitchPatternStyle.kanjium,
                (
                    '<span style="display:inline-block;position:relative;"><span style="display:inline;">ク</span>'
                    '<span style="border-color:currentColor;display:block;user-select:none;pointer-events:none;'
                    "position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;"
                    'border-top-style:solid;"></span></span>'
                ),
            ),
        ],
    )
    def test_convert_to_inline_style(
        self, txt: str, pitch_color: str, pitch_accent_style: HTMLPitchPatternStyle, expected: str
    ) -> None:
        """Each style produces its own markup, and the color placeholder is resolved."""
        assert convert_to_inline_style(txt, pitch_color, pitch_accent_style) == expected


class TestSortEntries:
    """Entries are sorted by katakana reading, then by pitch number."""

    @pytest.mark.parametrize(
        "entries, expected",
        [
            # Equal readings (ボク): the pitch number decides the order.
            ([ATAMADAKA_ENTRY, HEIBAN_ENTRY], [HEIBAN_ENTRY, ATAMADAKA_ENTRY]),
            # Already ordered by pitch number: the order is preserved.
            ([HEIBAN_ENTRY, ATAMADAKA_ENTRY], [HEIBAN_ENTRY, ATAMADAKA_ENTRY]),
            # Differing readings: the katakana reading decides the order (ガッコウ < ボク).
            ([HEIBAN_ENTRY, GAKKOU_ENTRY], [GAKKOU_ENTRY, HEIBAN_ENTRY]),
        ],
    )
    def test_sort_entries(self, entries: list[FormattedEntry], expected: list[FormattedEntry]) -> None:
        """Entries sort by katakana reading first, then by pitch number."""
        assert list(sort_entries(entries)) == expected


class TestUpdateHtml:
    """update_html applies the requested style, pitch color, and hiragana conversion."""

    @pytest.mark.parametrize(
        "entry, pitch_accent_style, expected",
        [
            # Default u_biq style: color is baked in.
            (HEIBAN_ENTRY, HTMLPitchPatternStyle.u_biq, HEIBAN_UBIQ),
            (ATAMADAKA_ENTRY, HTMLPitchPatternStyle.u_biq, ATAMADAKA_UBIQ),
            # Color-coded style: heiban color from the default config.
            (
                HEIBAN_ENTRY,
                HTMLPitchPatternStyle.u_biq_color_coded,
                (
                    '<span style="box-shadow: inset -2px -2px 0 0 #3366CC;">ボ</span>'
                    '<span style="box-shadow: inset 0px 2px 0 0px #3366CC;">ク</span>'
                ),
            ),
            # Color-coded style: atamadaka color from the default config.
            (
                ATAMADAKA_ENTRY,
                HTMLPitchPatternStyle.u_biq_color_coded,
                (
                    '<span style="box-shadow: inset -2px 2px 0 0px red;">ボ</span>'
                    '<span style="box-shadow: inset 0px -2px 0 0px red;">ク</span>'
                ),
            ),
            # javdejong style.
            (
                HEIBAN_ENTRY,
                HTMLPitchPatternStyle.javdejong,
                'ボ<span style="text-decoration:overline;">ク</span>',
            ),
        ],
    )
    def test_update_html(
        self,
        no_anki_config: NoAnkiConfigView,
        entry: FormattedEntry,
        pitch_accent_style: HTMLPitchPatternStyle,
        expected: str,
    ) -> None:
        """The requested style and the entry's pitch color are both applied."""
        formatter = EntryFormatter(no_anki_config)
        assert formatter.update_html(entry, pitch_accent_style) == expected

    def test_update_html_hiragana(self) -> None:
        """When output_hiragana is enabled, katakana inside spans is converted to hiragana."""
        cfg = make_fresh_config()
        cfg.pitch_accent["output_hiragana"] = True
        formatter = EntryFormatter(cfg)
        assert (
            formatter.update_html(HEIBAN_ENTRY, HTMLPitchPatternStyle.u_biq)
            == '<span style="box-shadow: inset -2px -2px 0 0 #FF6633;">ぼ</span>'
            '<span style="box-shadow: inset 0px 2px 0 0px #FF6633;">く</span>'
        )


class FormatPronunciationsScenario(typing.NamedTuple):
    """Scenario for format_pronunciations with explicit separators and limits."""

    pronunciations: AccentDict
    output_format: PitchOutputFormat
    max_results: int
    sep_single: str
    sep_multi: str
    expr_sep: str | None
    expected: str


class TestFormatPronunciations:
    """format_pronunciations joins styled entries with the configured separators."""

    @pytest.mark.parametrize(
        "scenario",
        [
            # Two entries for one word, separated by expr_sep and sep_single.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY, ATAMADAKA_ENTRY]},
                output_format=PitchOutputFormat.html,
                max_results=99,
                sep_single="・",
                sep_multi="、",
                expr_sep="：",
                expected=f"僕：{HEIBAN_UBIQ}・{ATAMADAKA_UBIQ}",
            ),
            # max_results truncates the entries.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY, ATAMADAKA_ENTRY]},
                output_format=PitchOutputFormat.html,
                max_results=1,
                sep_single="・",
                sep_multi="、",
                expr_sep="：",
                expected=f"僕：{HEIBAN_UBIQ}",
            ),
            # Two words are joined by sep_multi.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY], "学校": [GAKKOU_ENTRY]},
                output_format=PitchOutputFormat.html,
                max_results=99,
                sep_single="・",
                sep_multi="、",
                expr_sep="：",
                expected=f"僕：{HEIBAN_UBIQ}、学校：{GAKKOU_UBIQ}",
            ),
            # Without expr_sep, the words are omitted and only entries are joined.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY], "学校": [GAKKOU_ENTRY]},
                output_format=PitchOutputFormat.html,
                max_results=99,
                sep_single="・",
                sep_multi="、",
                expr_sep=None,
                expected=f"{HEIBAN_UBIQ}、{GAKKOU_UBIQ}",
            ),
            # Pitch numbers only.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY, ATAMADAKA_ENTRY]},
                output_format=PitchOutputFormat.number,
                max_results=99,
                sep_single="・",
                sep_multi="、",
                expr_sep="：",
                expected="僕：0・1",
            ),
            # HTML and number.
            FormatPronunciationsScenario(
                pronunciations={"僕": [HEIBAN_ENTRY, ATAMADAKA_ENTRY]},
                output_format=PitchOutputFormat.html_and_number,
                max_results=99,
                sep_single="・",
                sep_multi="、",
                expr_sep="：",
                expected=(
                    f'僕：{HEIBAN_UBIQ} <span class="pitch_number">0</span>'
                    f'・{ATAMADAKA_UBIQ} <span class="pitch_number">1</span>'
                ),
            ),
        ],
    )
    def test_format_pronunciations(
        self, no_anki_config: NoAnkiConfigView, scenario: FormatPronunciationsScenario
    ) -> None:
        """Entries and words are joined with the configured separators and truncated to max_results."""
        formatter = EntryFormatter(no_anki_config)
        assert (
            formatter.format_pronunciations(
                scenario.pronunciations,
                output_format=scenario.output_format,
                max_results=scenario.max_results,
                sep_single=scenario.sep_single,
                sep_multi=scenario.sep_multi,
                expr_sep=scenario.expr_sep,
            )
            == scenario.expected
        )

    def test_empty_pronunciations_format_to_empty_string(self, no_anki_config: NoAnkiConfigView) -> None:
        """Empty pronunciation mappings produce an empty output string."""
        assert EntryFormatter(no_anki_config).format_pronunciations({}, max_results=99) == ""

    def test_svg_output_matches_adapter(self, no_anki_config: NoAnkiConfigView) -> None:
        """The svg branch of the internal dispatcher renders through the adapter."""
        formatter = EntryFormatter(no_anki_config)
        assert formatter.format_pronunciations(
            {"僕": [HEIBAN_ENTRY]}, output_format=PitchOutputFormat.svg, max_results=3
        ) == FormattedEntryToSvgAdapter(no_anki_config).make_graph(HEIBAN_ENTRY)


class TestPronunciationsToJson:
    """pronunciations_to_json maps styled HTML keys to mora sequence dicts."""

    @pytest.mark.parametrize(
        "pronunciations, max_results, expected",
        [
            (
                {"僕": [HEIBAN_ENTRY]},
                99,
                (
                    {
                        "raw_headword": "僕",
                        "katakana_reading": "ボク",
                        "pitch_number": "0",
                        "pitch_type": "heiban",
                        "moras": [
                            {"txt": "ボ", "level": "low", "flags": []},
                            {"txt": "ク", "level": "high", "flags": []},
                        ],
                    },
                ),
            ),
            ({"僕": [HEIBAN_ENTRY]}, 0, ()),
        ],
    )
    def test_pronunciations_to_json(
        self,
        no_anki_config: NoAnkiConfigView,
        pronunciations: AccentDict,
        max_results: int,
        expected: Sequence[MoraSequenceOutputJson],
    ) -> None:
        """Each styled entry maps to one mora sequence dict, limited by max_results."""
        formatter = EntryFormatter(no_anki_config)
        assert tuple(formatter.pronunciations_to_json(pronunciations, max_results=max_results)) == expected

    def test_pronunciations_to_json_deduplicates_by_styled_html(self, no_anki_config: NoAnkiConfigView) -> None:
        """Entries with identical styled HTML collapse to one JSON mora sequence."""
        formatter = EntryFormatter(no_anki_config)

        assert tuple(
            formatter.pronunciations_to_json({"僕": [HEIBAN_ENTRY], "ボク": [HEIBAN_ENTRY]}, max_results=99)
        ) == (
            {
                "raw_headword": "僕",
                "katakana_reading": "ボク",
                "pitch_number": "0",
                "pitch_type": "heiban",
                "moras": [
                    {"txt": "ボ", "level": "low", "flags": []},
                    {"txt": "ク", "level": "high", "flags": []},
                ],
            },
        )


class TestSvgMakerInjection:
    """An injected SVG adapter is used instead of a newly constructed one."""

    def test_injected_svg_maker_is_used(self, no_anki_config: NoAnkiConfigView) -> None:
        """format_pronunciations renders SVGs through the injected adapter, not a new one."""
        svg_maker = create_autospec(FormattedEntryToSvgAdapter, instance=True)
        svg_maker.make_graph.return_value = "<svg>fake</svg>"
        formatter = EntryFormatter(no_anki_config, svg_maker=svg_maker)

        assert (
            formatter.format_pronunciations({"僕": [HEIBAN_ENTRY]}, output_format=PitchOutputFormat.svg, max_results=3)
            == "<svg>fake</svg>"
        )
        svg_maker.make_graph.assert_called_once_with(HEIBAN_ENTRY)
