# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.pitch_artist.artist_dialog import (
    format_graph_as_html,
    inject_css_into_svg,
    inline_css_code,
    make_graphs_list,
)
from japanese.pitch_artist.pitch_graph import SvgPitchArtistGraphMaker
from japanese.pitch_artist.split import (
    ArtistMora,
    SectionParts,
    detach_ghost_particle,
    split_multiple_pitch_notations,
    split_section,
    split_to_moras,
)
from playground.utils import NoAnkiConfigView


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("にほんご;-", "にほんご; -"),
        ("にほんご-", "にほんご -"),
    ],
)
def test_detach_ghost_particle(expression: str, expected: str) -> None:
    assert detach_ghost_particle(expression) == expected


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("にほんご", ["に", "ほ", "ん", "ご"]),
        ("を", ["を"]),
        ("べんきょう", ["べ", "ん", "きょ", "う"]),
        ("する", ["す", "る"]),
        ("おまえ", ["お", "ま", "え"]),
    ],
)
def test_split_to_moras(expression: str, expected: list[str]) -> None:
    assert split_to_moras(expression) == [ArtistMora.from_text(m) for m in expected]


def test_split_multiple_pitch_notations() -> None:
    """A section with comma-separated pitch notations expands into one sequence per notation."""
    assert split_multiple_pitch_notations([["にほんご;1,2,3", "を", "べんきょう;0", "する;"], ["おまえ;0"]]) == [
        ["にほんご;1", "を", "べんきょう;0", "する;"],
        ["にほんご;2", "を", "べんきょう;0", "する;"],
        ["にほんご;3", "を", "べんきょう;0", "する;"],
        ["おまえ;0"],
    ]


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("にほんご;1,2,3", SectionParts(word="にほんご", sep=";", accent="1,2,3")),
        ("にほんご", SectionParts(word="にほんご", sep=None, accent="")),
        ("にほんご;", SectionParts(word="にほんご", sep=";", accent="")),
        ("にほんご;h2", SectionParts(word="にほんご", sep=";", accent="h2")),
    ],
)
def test_split_section(expression: str, expected: SectionParts) -> None:
    assert split_section(expression) == expected


class TestArtistDialogHelpers:
    """Pure helpers used by the Pitch Artist dialog."""

    @pytest.mark.parametrize(
        "code, expected",
        [
            ("a { b: c; }", "a { b: c; }"),
            ("a {\n  b: c;\n}", "a { b: c; }"),
            ("  a   b  ", "a b"),
        ],
    )
    def test_inline_css_code(self, code: str, expected: str) -> None:
        """inline_css_code collapses newlines and whitespace runs into single spaces."""
        assert inline_css_code(code) == expected

    @pytest.mark.parametrize("index", [0, 3, 99])
    def test_format_graph_as_html(self, index: int) -> None:
        """format_graph_as_html wraps the graph and embeds a save button with the graph index."""
        assert (
            format_graph_as_html("<svg/>", index)
            == '<div class="svg_wrap"><div class="svg_graph"><svg/></div>'
            f'<button type="button" name="button" onclick="pycmd(\'ajt__save_graph:{index}\');">Save</button>'
            "</div>"
        )

    @pytest.mark.parametrize(
        "text, expected_count",
        [
            ("", 0),
            ("   ", 0),
            ("がっこう;0", 1),
            ("がっこう;0。つくった;2", 2),
        ],
    )
    def test_make_graphs_list(self, no_anki_config: NoAnkiConfigView, text: str, expected_count: int) -> None:
        """make_graphs_list returns one graph per parsed sequence, or none for empty text."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        assert len(make_graphs_list(text, gen)) == expected_count

    def test_inject_css_into_svg(self) -> None:
        """inject_css_into_svg inserts an inline <style> tag before the closing </svg>."""
        result = inject_css_into_svg('<svg class="ajt__pitch_svg"></svg>')
        assert result.startswith('<svg class="ajt__pitch_svg"><style>')
        assert result.endswith("</style></svg>")
        assert result.count("</svg>") == 1
