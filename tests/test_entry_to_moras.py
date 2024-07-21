# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence

import pytest

from japanese.pitch_accents.common import FormattedEntry, split_html_notation
from japanese.pitch_accents.entry_to_moras import (
    MoraFlag,
    PitchLevel,
    entry_to_moras,
    mora_flags2class_name,
)


def filter_by_level(moras, level: PitchLevel) -> Sequence[str]:
    return list(map(lambda mora: mora.txt, filter(lambda mora: mora.level == level and not mora.is_trailing(), moras)))


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

def test_entry_to_moras() -> None:
    e = FormattedEntry(
        "ジンチク",
        "<low_rise>ジ</low_rise><high>ン<devoiced>チ</devoiced>ク</high>",
        "0",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ンチク")
    assert filter_by_level(moras, PitchLevel.low) == list("ジ")
    assert moras[2].flags == MoraFlag.devoiced

    e = FormattedEntry(
        "ジンチク",
        "<high_drop>ジ</high_drop><low>ン<devoiced>チ</devoiced>ク</low>",
        "1",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ジ")
    assert filter_by_level(moras, PitchLevel.low) == list("ンチク")
    assert moras[2].flags == MoraFlag.devoiced

    e = FormattedEntry(
        "ジンセイテツガク",
        "<low_rise>ジ</low_rise><high_drop>ンセイテツ</high_drop><low>カ<nasal>&#176;</nasal>ク</low>",
        "6",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ンセイテツ")
    assert filter_by_level(moras, PitchLevel.low) == list("ジカク")
    assert moras[6].quark
    assert moras[6].quark.flags == MoraFlag.nasal

    e = FormattedEntry(
        "ジンセイテツガク",
        "<low_rise>ジ</low_rise><high_drop>ンセイテ</high_drop><low>ツカ<nasal>&#176;</nasal>ク</low>",
        "5",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ンセイテ")
    assert filter_by_level(moras, PitchLevel.low) == list("ジツカク")
    assert moras[6].quark
    assert moras[6].quark.flags == MoraFlag.nasal

    e = FormattedEntry(
        "イモウト",
        "<low_rise>イ</low_rise><high_drop>モート</high_drop>",
        "4",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("モート")
    assert filter_by_level(moras, PitchLevel.low) == list("イ")

    e = FormattedEntry(
        "ニジュウヨジカン",
        "<high_drop>ニ</high_drop><low>ジュー</low>・<low_rise>ヨ</low_rise><high_drop>ジ</high_drop><low>カン</low>",
        "1+2",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ニジ")
    assert filter_by_level(moras, PitchLevel.low) == ["ジュ", "ー", "ヨ", "カ", "ン"]

    e = FormattedEntry(
        "ニ",
        "<low_rise>ニ</low_rise>",
        "0",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("")
    assert filter_by_level(moras, PitchLevel.low) == list("ニ")

    e = FormattedEntry(
        "ヨ",
        "<high_drop>ヨ</high_drop>",
        "1",
    )
    moras = entry_to_moras(e).moras
    assert filter_by_level(moras, PitchLevel.high) == list("ヨ")
    assert filter_by_level(moras, PitchLevel.low) == list("")


def test_mora_flags2class_name() -> None:
    assert mora_flags2class_name(MoraFlag.nasal | MoraFlag.devoiced) == "nasal devoiced"
    assert mora_flags2class_name(MoraFlag.nasal) == "nasal"
    assert mora_flags2class_name(MoraFlag.devoiced) == "devoiced"
