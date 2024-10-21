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
from japanese.widgets.pitch_override_table import (
    PitchAccentTableRow,
    read_user_tsv_file,
)
from tests.conftest import tmp_user_accents_file


def test_user_tsv_entry() -> None:
    assert tuple(UserAccDictRawTSVEntry.__annotations__) == ("headword", "katakana_reading", "pitch_numbers")


@pytest.fixture(scope="session")
def fake_tsv():
    return [
        "A\tB\tC",
        "X\tY\tZ",
    ]


def szip(*args):
    try:
        return zip(*args, strict=True)
    except TypeError:
        # old python version
        return zip(*args)


def test_user_tsv_reader(fake_tsv) -> None:
    for row, expected in szip(get_user_tsv_reader(fake_tsv), fake_tsv):
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
    for formatted, expected in szip(formatted_from_tsv_row(test_input), expected_out):
        assert formatted == expected


def test_read_user_tsv_file(fake_tsv) -> None:
    for row, expected in szip(read_user_tsv_file(fake_tsv), fake_tsv):
        assert expected.split("\t") == list(row)


@pytest.fixture(scope="session")
def bad_fake_tsv():
    return [
        "A,B,C",
        "X,Y,Z",
    ]


def test_read_bad_user_tsv_file(bad_fake_tsv) -> None:
    for row, expected in szip(read_user_tsv_file(bad_fake_tsv), bad_fake_tsv):
        assert [expected, None, None] == list(row)


def test_read_user_tsv_file_from_disk(tmp_user_accents_file) -> None:
    expected_rows = [
        PitchAccentTableRow("言葉", "ソウシツ", "0"),
        PitchAccentTableRow("言葉", "ソゴ", "0"),
        PitchAccentTableRow("×××", "デタラメ", "0"),
    ]
    with open(tmp_user_accents_file, newline="", encoding="utf-8") as f:
        for row, expected in szip(read_user_tsv_file(f), expected_rows):
            assert row == expected
