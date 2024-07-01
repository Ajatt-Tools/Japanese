# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.mecab_controller.kana_conv import HIRAGANA, KATAKANA
from japanese.pitch_accents.basic_types import (
    PitchType,
    count_moras,
    pitch_type_from_pitch_num,
)


def test_count_moras() -> None:
    assert count_moras("あいうえお") == 5
    assert count_moras("カキクケコ") == 5
    assert count_moras("にゃ") == 1
    assert count_moras("あ") == 1
    assert count_moras("ー") == 1
    assert count_moras("っ") == 1
    assert count_moras("とうきょう") == 4
    assert count_moras("きゃきゅきょ") == 3


def test_pitch_type_from_pitch_num() -> None:
    assert pitch_type_from_pitch_num("0", 2) == PitchType.heiban
    assert pitch_type_from_pitch_num("1", 1) == PitchType.atamadaka
    assert pitch_type_from_pitch_num("2", 2) == PitchType.odaka
    assert pitch_type_from_pitch_num("2", 3) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("3", 3) == PitchType.odaka
    assert pitch_type_from_pitch_num("3", 10) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("4", 8) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("?", 8) == PitchType.unknown
