# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os.path

from japanese.mecab_controller.basic_types import Inflection, PartOfSpeech
from japanese.pitch_accents.basic_types import (
    AccDbParsedToken,
    PitchAccentEntry,
    PitchParam,
    PitchType,
)
from japanese.pitch_accents.common import (
    FormattedEntry,
    files_in_dir,
    split_pitch_numbers,
)
from japanese.pitch_accents.consts import PITCH_DIR_PATH
from japanese.pitch_accents.format_accents import format_entry


def test_pitch_accent_entry():
    entry = PitchAccentEntry.from_formatted(
        FormattedEntry(
            katakana_reading="たのしい",
            pitch_number="3",
            html_notation="",
        )
    )

    token = AccDbParsedToken(
        word="楽しかった",
        headword="楽しい",
        katakana_reading="たのしかった",
        part_of_speech=PartOfSpeech.i_adjective,
        inflection_type=Inflection.unknown,
        headword_accents=(entry,),
    )

    assert token.describe_pitches() == "たのしい:nakadaka-3"

    entry = PitchAccentEntry.from_formatted(
        FormattedEntry(
            katakana_reading="なや",
            pitch_number="0,1",
            html_notation="",
        )
    )

    token = AccDbParsedToken(
        word="納屋",
        headword="納屋",
        katakana_reading="なや",
        part_of_speech=PartOfSpeech.noun,
        inflection_type=Inflection.dictionary_form,
        headword_accents=(entry,),
    )
    assert token.describe_pitches() == "なや:heiban,atamadaka"

    token = AccDbParsedToken(
        word="粗末",
        headword="粗末",
        katakana_reading=None,
        part_of_speech=PartOfSpeech.unknown,
        inflection_type=Inflection.dictionary_form,
        headword_accents=[
            PitchAccentEntry(
                katakana_reading="ソマツ",
                pitches=[PitchParam(type=PitchType.atamadaka, number="1")],
            )
        ],
    )
    assert token.describe_pitches() == "ソマツ:atamadaka"


def test_files_in_dir():
    assert any(os.path.basename(file) == "__init__.py" for file in files_in_dir(PITCH_DIR_PATH))
    assert split_pitch_numbers("?-1-2") == ["?", "1", "2"]
    assert split_pitch_numbers("1") == ["1"]


def test_format_entry():
    assert format_entry(list("あいうえお"), 2) == "<low_rise>あ</low_rise><high_drop>い</high_drop><low>うえお</low>"
    assert format_entry(list("あいうえお"), 0) == "<low_rise>あ</low_rise><high>いうえお</high>"
    assert format_entry(list("あいうえお"), 1) == "<high_drop>あ</high_drop><low>いうえお</low>"
    assert format_entry(list("あ"), 1) == "<high_drop>あ</high_drop>"
    assert format_entry(list("あ"), 0) == "<low_rise>あ</low_rise>"
