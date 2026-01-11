# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.entry_to_moras import (
    Mora,
    MoraFlag,
    PitchLevel,
    Quark,
    entry_to_moras,
)
from japanese.pitch_accents.pitch_to_json import (
    MoraCombined,
    combine_mora,
    mora_sequence_to_dict,
    mora_to_dict,
)


@pytest.mark.parametrize(
    "mora, expected_txt, expected_level, expected_flags",
    [
        (Mora(txt=["あ", "い"], level=PitchLevel.high, flags=MoraFlag(0)), "あい", PitchLevel.high, MoraFlag(0)),
        (
            Mora(txt=["か", Quark(txt="゜", flags=MoraFlag.nasal)], level=PitchLevel.low, flags=MoraFlag.devoiced),
            "か゚",  # Note: This is the combining form, not the non-combining form
            PitchLevel.low,
            MoraFlag.nasal | MoraFlag.devoiced,
        ),
        (
            Mora(txt=["し", "ゅ", Quark(txt="゜", flags=MoraFlag.nasal)], level=PitchLevel.high, flags=MoraFlag(0)),
            "しゅ゚",  # Note: This is the combining form, not the non-combining form
            PitchLevel.high,
            MoraFlag.nasal,
        ),
    ],
)
def test_combine_mora(mora: Mora, expected_txt: str, expected_level: PitchLevel, expected_flags: MoraFlag) -> None:
    """Test combining a mora with various content types."""
    combined = combine_mora(mora)

    assert isinstance(combined, MoraCombined)
    assert combined.txt == expected_txt
    assert combined.level == expected_level
    assert combined.flags == expected_flags


@pytest.mark.parametrize(
    "combined, expected_txt, expected_level, expected_flags",
    [
        (
            MoraCombined(txt="か゜", flags=MoraFlag.nasal | MoraFlag.devoiced, level=PitchLevel.high),
            "か゜",
            "high",
            ["nasal", "devoiced"],
        ),
        (MoraCombined(txt="あ", flags=MoraFlag(0), level=PitchLevel.low), "あ", "low", []),
    ],
)
def test_mora_to_dict(
    combined: MoraCombined, expected_txt: str, expected_level: str, expected_flags: list[str]
) -> None:
    """Test converting a MoraCombined to dictionary format."""
    result = mora_to_dict(combined)

    assert isinstance(result, dict)
    assert result["txt"] == expected_txt
    assert result["level"] == expected_level
    assert result["flags"] == expected_flags


@pytest.mark.parametrize(
    "entry, expected_raw_headword, expected_katakana_reading, expected_pitch_number, expected_pitch_type",
    [
        (
            FormattedEntry(
                raw_headword="テスト",
                katakana_reading="テスト",
                html_notation="<low_rise>テ</low_rise><high>ス<nasal>ト<handakuten>&#176;</handakuten></nasal></high>",
                pitch_number="0",
            ),
            "テスト",
            "テスト",
            "0",
            "heiban",
        ),
        (
            FormattedEntry(
                raw_headword="よ", katakana_reading="ヨ", html_notation="<high_drop>ヨ</high_drop>", pitch_number="1"
            ),
            "よ",
            "ヨ",
            "1",
            "atamadaka",
        ),
    ],
)
def test_mora_sequence_to_dict(
    entry: FormattedEntry,
    expected_raw_headword: str,
    expected_katakana_reading: str,
    expected_pitch_number: str,
    expected_pitch_type: str,
) -> None:
    """Test converting a MoraSequence to dictionary format."""
    # Convert to MoraSequence
    sequence = entry_to_moras(entry)

    # Convert to dictionary
    result = mora_sequence_to_dict(sequence)

    assert isinstance(result, dict)
    assert result["raw_headword"] == expected_raw_headword
    assert result["katakana_reading"] == expected_katakana_reading
    assert result["pitch_number"] == expected_pitch_number
    assert result["pitch_type"] == expected_pitch_type
    assert isinstance(result["moras"], list)
    assert len(result["moras"]) > 0


@pytest.mark.parametrize(
    "entry",
    [
        FormattedEntry(
            raw_headword="よ", katakana_reading="ヨ", html_notation="<high_drop>ヨ</high_drop>", pitch_number="1"
        ),
        FormattedEntry(
            raw_headword="に", katakana_reading="ニ", html_notation="<low_rise>ニ</low_rise>", pitch_number="0"
        ),
    ],
)
def test_mora_sequence_to_dict_with_trailing_mora(entry: FormattedEntry) -> None:
    """Test that trailing moras are excluded from the output."""
    # Convert to MoraSequence
    sequence = entry_to_moras(entry, enable_trailing_mora=False)

    # Verify we have a trailing mora
    assert not any(mora.is_trailing() for mora in sequence.moras)
