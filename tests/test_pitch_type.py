# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.pitch_accents.basic_types import pitch_type_from_pitch_num, PitchType


def test_pitch_type_from_pitch_num() -> None:
    assert pitch_type_from_pitch_num("0", 2) == PitchType.heiban
    assert pitch_type_from_pitch_num("1", 1) == PitchType.atamadaka
    assert pitch_type_from_pitch_num("2", 2) == PitchType.odaka
    assert pitch_type_from_pitch_num("2", 3) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("3", 3) == PitchType.odaka
    assert pitch_type_from_pitch_num("3", 10) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("4", 8) == PitchType.nakadaka
    assert pitch_type_from_pitch_num("?", 8) == PitchType.unknown
