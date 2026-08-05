# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.pitch_artist.split import (
    ArtistMora,
    SectionParts,
    detach_ghost_particle,
    split_multiple_pitch_notations,
    split_section,
    split_to_moras,
)


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
