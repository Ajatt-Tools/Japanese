# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.mecab_controller.basic_types import PartOfSpeech
from japanese.mecab_controller.kana_conv import HIRAGANA, KATAKANA
from japanese.pitch_accents.basic_types import (
    PitchParam,
    PitchType,
    PitchUnknown,
    adjust_if_kifuku,
    count_moras,
    is_verb_or_i_adjective,
    pitch_type_from_pitch_num,
)


@pytest.mark.parametrize(
    "text_case,  expected_mora_count",
    [
        ("あいうえお", 5),
        ("カキクケコ", 5),
        ("にゃ", 1),
        ("あ", 1),
        ("ー", 1),
        ("っ", 1),
        ("とうきょう", 4),
        ("きゃきゅきょ", 3),
    ],
)
def test_count_moras(text_case: str, expected_mora_count: int) -> None:
    assert count_moras(text_case) == expected_mora_count


@pytest.mark.parametrize(
    "pitch_num_str,  n_moras,  expected_type",
    [
        ("0", 2, PitchType.heiban),
        ("0", 9, PitchType.heiban),
        ("1", 1, PitchType.atamadaka),
        ("1", 9, PitchType.atamadaka),
        ("2", 2, PitchType.odaka),
        ("3", 3, PitchType.odaka),
        ("4", 4, PitchType.odaka),
        ("2", 3, PitchType.nakadaka),
        ("3", 10, PitchType.nakadaka),
        ("4", 8, PitchType.nakadaka),
        ("?", 8, PitchType.unknown),
        ("xxx", 8, PitchType.unknown),
    ],
)
def test_pitch_type_from_pitch_num(pitch_num_str: str, n_moras: int, expected_type: PitchType) -> None:
    assert pitch_type_from_pitch_num(pitch_num_str, n_moras) == expected_type


@pytest.mark.parametrize(
    "pitch_num_str,  n_moras",
    [
        ("-2", 2),
        ("-1", 1),
        ("0", -1),
        ("1", 0),
        ("3", -2),
        ("33", 10),
        ("44", 3),
    ],
)
def test_pitch_type_from_pitch_num_value_error(pitch_num_str: str, n_moras: int) -> None:
    with pytest.raises(ValueError):
        pitch_type_from_pitch_num(pitch_num_str, n_moras)


@pytest.mark.parametrize(
    "part_of_speech,  expected_result",
    [
        (PartOfSpeech.verb, True),
        (PartOfSpeech.i_adjective, True),
        (PartOfSpeech.noun, False),
        (PartOfSpeech.adverb, False),
        (PartOfSpeech.unknown, False),
    ],
)
def test_is_verb_or_i_adjective(part_of_speech: PartOfSpeech, expected_result: bool) -> None:
    """Test the is_verb_or_i_adjective function."""
    assert is_verb_or_i_adjective(part_of_speech) is expected_result


@pytest.mark.parametrize(
    "part_of_speech,  pitch_type,  expected_result",
    [
        # Non-heiban verbs should be adjusted to kifuku
        (PartOfSpeech.verb, PitchType.atamadaka, PitchType.kifuku),
        (PartOfSpeech.verb, PitchType.nakadaka, PitchType.kifuku),
        (PartOfSpeech.verb, PitchType.odaka, PitchType.kifuku),
        # Heiban verbs should not be adjusted
        (PartOfSpeech.verb, PitchType.heiban, PitchType.heiban),
        # Non-heiban i-adjectives should be adjusted to kifuku
        (PartOfSpeech.i_adjective, PitchType.atamadaka, PitchType.kifuku),
        (PartOfSpeech.i_adjective, PitchType.nakadaka, PitchType.kifuku),
        (PartOfSpeech.i_adjective, PitchType.odaka, PitchType.kifuku),
        # Heiban i-adjectives should not be adjusted
        (PartOfSpeech.i_adjective, PitchType.heiban, PitchType.heiban),
        # Other parts of speech should not be adjusted
        (PartOfSpeech.noun, PitchType.atamadaka, PitchType.atamadaka),
        (PartOfSpeech.noun, PitchType.nakadaka, PitchType.nakadaka),
        (PartOfSpeech.adverb, PitchType.atamadaka, PitchType.atamadaka),
        (PartOfSpeech.bound_auxiliary, PitchType.odaka, PitchType.odaka),
        # Kifuku should not be adjusted
        (PartOfSpeech.bound_auxiliary, PitchType.kifuku, PitchType.kifuku),
        (PartOfSpeech.verb, PitchType.kifuku, PitchType.kifuku),
        (PartOfSpeech.i_adjective, PitchType.kifuku, PitchType.kifuku),
        # Unknown parts of speech should not be adjusted
        (PartOfSpeech.unknown, PitchType.atamadaka, PitchType.atamadaka),
        (PartOfSpeech.unknown, PitchType.unknown, PitchType.unknown),
        (PartOfSpeech.unknown, PitchType.heiban, PitchType.heiban),
        # Unknown pitch types should not be adjusted
        (PartOfSpeech.verb, PitchType.unknown, PitchType.unknown),
    ],
)
def test_adjust_if_kifuku(part_of_speech: PartOfSpeech, pitch_type: PitchType, expected_result: PitchType) -> None:
    """Test the adjust_if_kifuku function."""
    assert adjust_if_kifuku(part_of_speech, pitch_type) == expected_result


@pytest.mark.parametrize(
    "pitch_type,  pitch_num,  n_moras,  expected_description",
    [
        (PitchType.kifuku, "2", 3, "kifuku-2"),
        (PitchType.kifuku, "33", 33, "kifuku-33"),
        (PitchType.nakadaka, "3", 6, "nakadaka-3"),
        (PitchType.atamadaka, "1", 8, "atamadaka"),
        (PitchType.heiban, "0", 3, "heiban"),
        (PitchType.heiban, "0", 4, "heiban"),
        (PitchType.odaka, "3", 3, "odaka"),
        (PitchType.odaka, "6", 6, "odaka"),
        (PitchType.unknown, "2", 3, "unknown"),
    ],
)
def test_pitch_param_describe(pitch_type: PitchType, pitch_num: str, n_moras: int, expected_description: str) -> None:
    """Test that PitchParam.describe() handles all pitch types correctly."""
    param = PitchParam(type=pitch_type, number=pitch_num, n_moras=n_moras)
    assert param.describe() == expected_description
