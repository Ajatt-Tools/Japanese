# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import typing
from collections.abc import Sequence

import pytest

from japanese.pitch_accents.basic_types import PitchType
from japanese.pitch_accents.common import FormattedEntry, split_html_notation
from japanese.pitch_accents.entry_to_moras import (
    MoraFlag,
    PitchLevel,
    Quark,
    entry_to_moras,
    html_notation_to_moras,
    mora_flags2class_name,
)

CIRCLE = "°"


def filter_by_level(moras, level: PitchLevel) -> Sequence[str]:
    return list(map(lambda mora: mora.txt, filter(lambda mora: mora.level == level and not mora.is_trailing(), moras)))


def mora_char_to_str(char: typing.Union[Quark, str]) -> str:
    return char if isinstance(char, str) else CIRCLE


@pytest.mark.parametrize(
    "html_notation, expected",
    [
        (
            "<low_rise>ア</low_rise><high>ク<nasal>キ<handakuten>&#176;</handakuten></nasal>ャク</high>",
            [
                "<low_rise>",
                "ア",
                "</low_rise>",
                "<high>",
                "ク",
                "<nasal>",
                "キ",
                "<handakuten>",
                "&#176;",
                "</handakuten>",
                "</nasal>",
                "ャク",
                "</high>",
            ],
        ),
        (
            "<low_rise>ト</low_rise><high_drop><devoiced>シ</devoiced>ュタ</high_drop><low>イソー</low>",
            [
                "<low_rise>",
                "ト",
                "</low_rise>",
                "<high_drop>",
                "<devoiced>",
                "シ",
                "</devoiced>",
                "ュタ",
                "</high_drop>",
                "<low>",
                "イソー",
                "</low>",
            ],
        ),
    ],
)
def test_split_html_notation(html_notation: str, expected: list[str]) -> None:
    assert list(split_html_notation(html_notation)) == expected


@pytest.mark.parametrize(
    "html_notation, expected",
    [
        (
            "<low_rise>ア</low_rise><high>ク<nasal>キ<handakuten>&#176;</handakuten></nasal>ャク</high>",
            ["ア", "ク", f"キ{CIRCLE}ャ", "ク"],
        ),
        (
            "<low_rise>ト</low_rise><high_drop><devoiced>シ</devoiced>ュタ</high_drop><low>イソー</low>",
            ["ト", "シュ", "タ", "イ", "ソ", "ー"],
        ),
    ],
)
def test_html_notation_to_moras(html_notation: str, expected: list[str]) -> None:
    moras = html_notation_to_moras(html_notation)
    as_list_str = ["".join(mora_char_to_str(char) for char in mora.txt) for mora in moras]
    assert as_list_str == expected


@pytest.mark.parametrize(
    "entry, expected_hl, pitch_type, devoiced_pos, nasal_pos",
    [
        (
            FormattedEntry(
                "ジンチク",
                "<low_rise>ジ</low_rise><high>ン<devoiced>チ</devoiced>ク</high>",
                "0",
            ),
            ["ジ:L", "ン:H", "チ:H", "ク:H", ":H"],
            PitchType.heiban,
            [2],
            [],
        ),
        (
            FormattedEntry(
                "ジンチク",
                "<high_drop>ジ</high_drop><low>ン<devoiced>チ</devoiced>ク</low>",
                "1",
            ),
            ["ジ:H", "ン:L", "チ:L", "ク:L"],
            PitchType.atamadaka,
            [2],
            [],
        ),
        (
            FormattedEntry(
                "ジンセイテツガク",
                "<low_rise>ジ</low_rise><high_drop>ンセイテツ</high_drop><low><nasal>カ<handakuten>&#176;</handakuten></nasal>ク</low>",
                "6",
            ),
            ["ジ:L", "ン:H", "セ:H", "イ:H", "テ:H", "ツ:H", f"カ{CIRCLE}:L", "ク:L"],
            PitchType.nakadaka,
            [],
            [6],
        ),
        (
            FormattedEntry(
                "ジンセイテツガク",
                "<low_rise>ジ</low_rise><high_drop>ンセイテ</high_drop><low>ツ<nasal>カ<handakuten>&#176;</handakuten></nasal>ク</low>",
                "5",
            ),
            ["ジ:L", "ン:H", "セ:H", "イ:H", "テ:H", "ツ:L", f"カ{CIRCLE}:L", "ク:L"],
            PitchType.nakadaka,
            [],
            [6],
        ),
        (
            FormattedEntry(
                "イモウト",
                "<low_rise>イ</low_rise><high_drop>モート</high_drop>",
                "4",
            ),
            ["イ:L", "モ:H", "ー:H", "ト:H"],
            PitchType.odaka,
            [],
            [],
        ),
        (
            FormattedEntry(
                "ニジュウヨジカン",
                "<high_drop>ニ</high_drop><low>ジュー</low>・<low_rise>ヨ</low_rise><high_drop>ジ</high_drop><low>カン</low>",
                "1+2",
            ),
            ["ニ:H", "ジュ:L", "ー:L", "ヨ:L", "ジ:H", "カ:L", "ン:L"],
            PitchType.unknown,
            [],
            [],
        ),
        (
            FormattedEntry(
                "ニ",
                "<low_rise>ニ</low_rise>",
                "0",
            ),
            ["ニ:L", ":H"],
            PitchType.heiban,
            [],
            [],
        ),
        (
            FormattedEntry(
                "ヨ",
                "<high_drop>ヨ</high_drop>",
                "1",
            ),
            ["ヨ:H", ":L"],
            PitchType.atamadaka,
            [],
            [],
        ),
    ],
)
def test_entry_to_moras(
    entry: FormattedEntry, expected_hl: list[str], pitch_type: PitchType, devoiced_pos: list[int], nasal_pos: list[int]
) -> None:
    def mora_text_to_str(mora_txt: list[typing.Union[str, Quark]]) -> str:
        return "".join(mora_char_to_str(char) for char in mora_txt)

    moras = entry_to_moras(entry)
    as_list_str = [f"{mora_text_to_str(mora.txt)}:{mora.level.name[0].upper()}" for mora in moras.moras]
    assert as_list_str == expected_hl
    assert moras.pitch_type == pitch_type
    assert all(MoraFlag.devoiced in moras.moras[pos].flags for pos in devoiced_pos)
    assert all(MoraFlag.nasal in moras.moras[pos].flags for pos in nasal_pos)


def test_mora_flags2class_name() -> None:
    assert mora_flags2class_name(MoraFlag.nasal | MoraFlag.devoiced) == "nasal devoiced"
    assert mora_flags2class_name(MoraFlag.nasal) == "nasal"
    assert mora_flags2class_name(MoraFlag.devoiced) == "devoiced"
