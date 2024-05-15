# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence

from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.entry_to_moras import entry_to_moras, PitchLevel, MoraFlag, mora_flags_to_classname


def filter_by_level(moras, level: PitchLevel) -> Sequence[str]:
    return list(map(lambda mora: mora.txt, filter(lambda mora: mora.level == level, moras)))


def test_entry_to_moras() -> None:
    e = FormattedEntry(
        "ジンチク",
        "<low_rise>ジ</low_rise><high>ン<devoiced>チ</devoiced>ク</high>",
        "0",
    )
    moras = entry_to_moras(e)
    assert filter_by_level(moras, PitchLevel.high) == list("ンチク")
    assert filter_by_level(moras, PitchLevel.low) == list("ジ")
    assert moras[2].flags == MoraFlag.devoiced

    e = FormattedEntry(
        "ジンチク",
        "<high_drop>ジ</high_drop><low>ン<devoiced>チ</devoiced>ク</low>",
        "1",
    )
    moras = entry_to_moras(e)
    assert filter_by_level(moras, PitchLevel.high) == list("ジ")
    assert filter_by_level(moras, PitchLevel.low) == list("ンチク")
    assert moras[2].flags == MoraFlag.devoiced

    e = FormattedEntry(
        "ジンセイテツガク",
        "<low_rise>ジ</low_rise><high_drop>ンセイテツ</high_drop><low>カ<nasal>&#176;</nasal>ク</low>",
        "6",
    )
    moras = entry_to_moras(e)
    assert filter_by_level(moras, PitchLevel.high) == list("ンセイテツ")
    assert filter_by_level(moras, PitchLevel.low) == list("ジカク")
    assert moras[6].quark.flags == MoraFlag.nasal

    e = FormattedEntry(
        "ジンセイテツガク",
        "<low_rise>ジ</low_rise><high_drop>ンセイテ</high_drop><low>ツカ<nasal>&#176;</nasal>ク</low>",
        "5",
    )
    moras = entry_to_moras(e)
    assert filter_by_level(moras, PitchLevel.high) == list("ンセイテ")
    assert filter_by_level(moras, PitchLevel.low) == list("ジツカク")
    assert moras[6].quark.flags == MoraFlag.nasal

    e = FormattedEntry(
        "イモウト",
        "<low_rise>イ</low_rise><high_drop>モート</high_drop>",
        "4",
    )
    moras = entry_to_moras(e)
    assert filter_by_level(moras, PitchLevel.high) == list("モート")
    assert filter_by_level(moras, PitchLevel.low) == list("イ")


def test_mora_flags_to_classname() -> None:
    assert mora_flags_to_classname(MoraFlag.nasal | MoraFlag.devoiced) == "nasal devoiced"
    assert mora_flags_to_classname(MoraFlag.nasal) == "nasal"
    assert mora_flags_to_classname(MoraFlag.devoiced) == "devoiced"
