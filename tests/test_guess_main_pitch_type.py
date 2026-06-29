# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from typing import Union

import pytest

from japanese.furigana.color_code_wrapper import guess_main_pitch_type
from japanese.mecab_controller.basic_types import Inflection, PartOfSpeech
from japanese.pitch_accents.basic_types import (
    AccDbParsedToken,
    PitchAccentEntry,
    PitchParam,
    PitchType,
    PitchUnknown,
)


@pytest.mark.parametrize(
    "accents,  expected_pitch",
    [
        ([2], PitchType.kifuku),
        ([], PitchUnknown.none),
        ([0, 1, 2], PitchUnknown.many),
        ([0, 1], PitchUnknown.many),
        ([], PitchUnknown.none),
        ([1, 1, 1], PitchType.kifuku),
        ([2, 2, 2], PitchType.kifuku),
        ([0, 0], PitchType.heiban),
    ],
)
def test_guess_main_pitch_type_verb(accents: list[int], expected_pitch: PitchUnknown | PitchType) -> None:
    """Test that guess_main_pitch_type returns PitchUnknown.many for multiple different accents."""
    token = AccDbParsedToken(
        word="食べる",
        headword="食べる",
        katakana_reading="タベル",
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading="タベル",
                katakana_reading_sep="タベル",
                pitches=[PitchParam.from_symbol("タベル", str(pitch_num), PartOfSpeech.verb)],
            )
            for pitch_num in accents
        ],
    )
    assert guess_main_pitch_type(token) == expected_pitch


@pytest.mark.parametrize(
    "pitch_type,  pitch_num,  n_moras,  expected_result",
    [
        (PitchType.atamadaka, "1", 2, PitchType.atamadaka),
        (PitchType.heiban, "0", 2, PitchType.heiban),
        (PitchType.nakadaka, "2", 3, PitchType.nakadaka),
        (PitchType.odaka, "3", 3, PitchType.odaka),
        (PitchType.kifuku, "1", 2, PitchType.kifuku),
    ],
)
def test_guess_main_pitch_type_single_pitch(
    pitch_type: PitchType, pitch_num: str, n_moras: int, expected_result: PitchType
) -> None:
    """Test that guess_main_pitch_type returns the single pitch type when there's only one."""
    token = AccDbParsedToken(
        word="食べる",
        headword="食べる",
        katakana_reading="タベル",
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading="タベル",
                katakana_reading_sep="タベル",
                pitches=[PitchParam(type=pitch_type, number=pitch_num, n_moras=n_moras)],
            )
        ],
    )

    assert guess_main_pitch_type(token) == expected_result


@pytest.mark.parametrize(
    "pitch_type,  n_repeat",
    [
        (PitchType.atamadaka, 1),
        (PitchType.atamadaka, 33),
        (PitchType.heiban, 2),
        (PitchType.heiban, 3),
        (PitchType.nakadaka, 1),
        (PitchType.nakadaka, 2),
        (PitchType.nakadaka, 3),
        (PitchType.odaka, 3),
        (PitchType.kifuku, 2),
    ],
)
def test_guess_main_pitch_type_multiple_same_pitch(pitch_type: PitchType, n_repeat: int) -> None:
    """Test that guess_main_pitch_type returns the common pitch type when all are the same."""
    token = AccDbParsedToken(
        word="食べる",
        headword="食べる",
        katakana_reading="タベル",
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading="タベル",
                katakana_reading_sep="タベル",
                pitches=[PitchParam(type=pitch_type, number="1", n_moras=3) for _ in range(n_repeat)],
            )
            for _ in range(n_repeat)
        ],
    )

    assert guess_main_pitch_type(token) == pitch_type


@pytest.mark.parametrize(
    "pitch_types",
    [
        [PitchType.atamadaka, PitchType.heiban],
        [PitchType.nakadaka, PitchType.odaka],
        [PitchType.heiban, PitchType.odaka],
        [PitchType.kifuku, PitchType.heiban],
        [PitchType.atamadaka, PitchType.nakadaka, PitchType.odaka],
        [PitchType.heiban, PitchType.kifuku, PitchType.atamadaka, PitchType.nakadaka],
        [PitchType.kifuku, PitchType.heiban, PitchType.kifuku, PitchType.atamadaka, PitchType.nakadaka],
        [PitchType.heiban, PitchType.kifuku, PitchType.atamadaka, PitchType.nakadaka],
        [
            PitchType.heiban,
            PitchType.atamadaka,
            PitchType.atamadaka,
            PitchType.atamadaka,
        ],
        [pitch_type for pitch_type in PitchType],
    ],
)
def test_guess_main_pitch_type_multiple_different_pitch(pitch_types: list[PitchType]) -> None:
    """Test that guess_main_pitch_type returns PitchUnknown.many when there are different pitch types."""
    token = AccDbParsedToken(
        word="食べる",
        headword="食べる",
        katakana_reading="タベル",
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading="タベル",
                katakana_reading_sep="タベル",
                # note: guess_main_pitch_type() doesn't take numbers into account.
                pitches=[PitchParam(type=pitch_type, number="1", n_moras=1)],
            )
            for pitch_type in pitch_types
        ],
    )
    assert guess_main_pitch_type(token) == PitchUnknown.many


@pytest.mark.parametrize(
    "word,  headword,  katakana_reading",
    [
        ("食べる", "食べる", "タベル"),
        ("見る", "見る", "ミル"),
        ("話す", "話す", "ハナス"),
        ("美しい", "美しい", "ウツクシイ"),
        ("高い", "高い", "タカイ"),
    ],
)
def test_guess_main_pitch_type_no_pitch(word: str, headword: str, katakana_reading: str) -> None:
    """Test that guess_main_pitch_type returns PitchUnknown.none when there are no pitch accents."""
    token = AccDbParsedToken(
        word=word,
        headword=headword,
        katakana_reading=katakana_reading,
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[],
    )
    assert guess_main_pitch_type(token) == PitchUnknown.none


@pytest.mark.parametrize(
    "word,  headword,  katakana_reading,  n_repeat",
    [
        ("食べる", "食べる", "タベル", 1),
        ("食べる", "食べる", "タベル", 2),
        ("見る", "見る", "ミル", 3),
        ("話す", "話す", "ハナス", 4),
        ("美しい", "美しい", "ウツクシイ", 5),
        ("高い", "高い", "タカイ", 6),
    ],
)
def test_guess_main_pitch_type_empty_pitches(word: str, headword: str, katakana_reading: str, n_repeat: int) -> None:
    """Test that guess_main_pitch_type returns PitchUnknown.none when there are entries but no pitches."""
    token = AccDbParsedToken(
        word=word,
        headword=headword,
        katakana_reading=katakana_reading,
        part_of_speech=PartOfSpeech.verb,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading=katakana_reading,
                katakana_reading_sep=katakana_reading,
                pitches=[],
            )
            for _ in range(n_repeat)
        ],
    )
    assert guess_main_pitch_type(token) == PitchUnknown.none
