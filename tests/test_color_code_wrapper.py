# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from typing import Union

import pytest

from japanese.furigana.color_code_wrapper import ColorCodeWrapper, guess_main_pitch_type
from japanese.helpers.profiles import ColorCodePitchFormat
from japanese.mecab_controller.basic_types import Inflection, PartOfSpeech
from japanese.pitch_accents.basic_types import (
    AccDbParsedToken,
    PitchAccentEntry,
    PitchParam,
    PitchType,
    PitchUnknown,
)
from playground.utils import NoAnkiConfigView


@pytest.mark.parametrize(
    "word,  katakana_reading,  part_of_speech,  pitch_number,  expected_pitch_attr",
    [
        ("食べる", "タベル", PartOfSpeech.verb, "1", 'pitch="タベル:kifuku-1"'),
        ("食べる", "タベル", PartOfSpeech.verb, "2", 'pitch="タベル:kifuku-2"'),
        ("食べる", "タベル", PartOfSpeech.verb, "3", 'pitch="タベル:kifuku-3"'),
        ("食べる", "タベル", PartOfSpeech.verb, "0", 'pitch="タベル:heiban"'),
        ("高い", "タカイ", PartOfSpeech.i_adjective, "2", 'pitch="タカイ:kifuku-2"'),
        ("美しい", "ウツクシイ", PartOfSpeech.i_adjective, "3", 'pitch="ウツクシイ:kifuku-3"'),
        ("あける", "アケル", PartOfSpeech.verb, "0", 'pitch="アケル:heiban"'),
        ("あける", "アケル", PartOfSpeech.verb, "2", 'pitch="アケル:kifuku-2"'),
        ("電話", "デンワ", PartOfSpeech.noun, "1", 'pitch="デンワ:atamadaka"'),
    ],
)
def test_color_code_wrapper_kifuku(
    no_anki_config: NoAnkiConfigView,
    word: str,
    katakana_reading: str,
    part_of_speech: PartOfSpeech,
    pitch_number: str,
    expected_pitch_attr: str,
) -> None:
    """Test that ColorCodeWrapper correctly handles kifuku pitch types."""
    token = AccDbParsedToken(
        word=word,
        headword=word,
        katakana_reading=katakana_reading,
        part_of_speech=part_of_speech,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading=katakana_reading,
                katakana_reading_sep=katakana_reading,
                pitches=[PitchParam.from_symbol(katakana_reading, pitch_number, part_of_speech)],
            )
        ],
    )

    # Test with attributes only format
    with ColorCodeWrapper(token, ColorCodePitchFormat.attributes, cfg=no_anki_config) as wrapper:
        result = wrapper.getvalue()

    # Should contain kifuku in the pitch attribute
    assert expected_pitch_attr in result
    # Should have the ajt__word_info class
    assert 'class="ajt__word_info"' in result
