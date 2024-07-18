# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence

import pytest

from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.user_accents import (
    UserAccDictRawTSVEntry,
    formatted_from_tsv_row,
    get_user_tsv_reader,
)


def test_user_tsv_entry() -> None:
    assert tuple(UserAccDictRawTSVEntry.__annotations__) == ("headword", "katakana_reading", "pitch_numbers")


@pytest.fixture(scope="session")
def fake_tsv():
    return [
        "A\tB\tC",
        "X\tY\tZ",
    ]


def test_user_tsv_reader(fake_tsv) -> None:
    for row, expected in zip(get_user_tsv_reader(fake_tsv), fake_tsv):
        assert tuple(row.keys()) == tuple(UserAccDictRawTSVEntry.__annotations__)
        assert list(row.values()) == expected.split("\t")


@pytest.mark.parametrize(
    "test_input, expected_out",
    [
        (
            UserAccDictRawTSVEntry(headword="遙遙", katakana_reading="はるばる", pitch_numbers="3,2"),
            (
                FormattedEntry(
                    katakana_reading="ハルバル",
                    pitch_number="3",
                    html_notation="<low_rise>ハ</low_rise><high_drop>ルバ</high_drop><low>ル</low>",
                ),
                FormattedEntry(
                    katakana_reading="ハルバル",
                    pitch_number="2",
                    html_notation="<low_rise>ハ</low_rise><high_drop>ル</high_drop><low>バル</low>",
                ),
            ),
        ),
        (
            UserAccDictRawTSVEntry(headword="溝渠", katakana_reading="コウキョ", pitch_numbers="1"),
            (
                FormattedEntry(
                    katakana_reading="コウキョ",
                    pitch_number="1",
                    html_notation="<high_drop>コ</high_drop><low>ウキョ</low>",
                ),
            ),
        ),
    ],
)
def test_formatted_from_tsv_row(test_input: UserAccDictRawTSVEntry, expected_out: Sequence[FormattedEntry]) -> None:
    for formatted, expected in zip(formatted_from_tsv_row(test_input), expected_out):
        assert formatted == expected
