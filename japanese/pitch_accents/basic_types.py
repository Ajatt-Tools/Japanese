# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
from collections.abc import MutableSequence, Sequence
from typing import NamedTuple

from ..mecab_controller.basic_types import Inflection, MecabParsedToken, PartOfSpeech
from ..mecab_controller.kana_conv import kana_to_moras
from .common import FormattedEntry, split_pitch_numbers
from .consts import NO_ACCENT

SEP_PITCH_GROUP = " "
SEP_PITCH_TYPES = ","
SEP_READING_PITCH = ":"
SEP_PITCH_TYPE_NUM = "-"


@enum.unique
class PitchType(enum.Enum):
    unknown = NO_ACCENT
    heiban = 0
    atamadaka = 1
    nakadaka = object()
    odaka = object()
    kifuku = object()


@enum.unique
class PitchColor(enum.Enum):
    heiban = "#3366CC"  # blue
    atamadaka = "red"
    nakadaka = "#eb8500"  # orange
    odaka = "green"
    kifuku = "purple"
    unknown = "gray"


def pitch_type_from_pitch_num(pitch_num_as_str: str, n_moras: int) -> PitchType:
    if not pitch_num_as_str:
        return PitchType.unknown

    try:
        pitch_num = int(pitch_num_as_str)
    except ValueError:
        # pitch num is not a number => pitch is unknown
        return PitchType.unknown

    assert pitch_num >= 0, "pitch number can't be less than 0"
    assert n_moras > 0, "word must consist of at least 1 mora"
    assert pitch_num <= n_moras, "pitch must drop inside the word or right after"

    if pitch_num == 0:
        return PitchType.heiban
    if pitch_num == 1:
        return PitchType.atamadaka
    if pitch_num == n_moras:
        return PitchType.odaka
    if pitch_num < n_moras:
        return PitchType.nakadaka
    return PitchType.unknown


class PitchParam(NamedTuple):
    type: PitchType
    number: str

    def describe(self):
        if self.type == PitchType.nakadaka:
            return f"{self.type.name}{SEP_PITCH_TYPE_NUM}{self.number}"
        else:
            return self.type.name

    @classmethod
    def from_symbol(cls, katakana_reading: str, pitch_num_as_str: str):
        return cls(
            type=pitch_type_from_pitch_num(pitch_num_as_str, n_moras=len(kana_to_moras(katakana_reading))),
            number=pitch_num_as_str,
        )


class PitchAccentEntry(NamedTuple):
    katakana_reading: str
    pitches: list[PitchParam]

    def has_accent(self) -> bool:
        return bool(self.pitches and any(pitch.type != PitchType.unknown for pitch in self.pitches))

    def describe_pitches(self) -> str:
        return (
            self.katakana_reading
            + SEP_READING_PITCH
            + SEP_PITCH_TYPES.join(dict.fromkeys(pitch.describe() for pitch in self.pitches))
        )

    @classmethod
    def from_formatted(cls, entry: FormattedEntry) -> "PitchAccentEntry":
        """
        Construct cls from a dictionary entry.

        Pitch number is stored as a string in the pitch accents CSV file.
        The string can either be directly convertible to int, indicate that the pitch is unknown,
        or contain more than one number.
        """
        return cls(
            katakana_reading=entry.katakana_reading,
            pitches=[
                PitchParam.from_symbol(entry.katakana_reading, symbol)
                for symbol in split_pitch_numbers(entry.pitch_number)
            ],
        )


@dataclasses.dataclass(frozen=True)
class AccDbParsedToken(MecabParsedToken):
    """
    Add pitch number to the parsed token
    """

    headword_accents: Sequence[PitchAccentEntry]
    # Attached tokens are stored in this list to apply pitch color-code to them.
    attached_tokens: MutableSequence[str] = dataclasses.field(default_factory=list)

    def describe_pitches(self) -> str:
        """
        reading1:pitch_type reading2:pitch_type
        コッキョウ:heiban クニザカイ:nakadaka-3
        """
        return SEP_PITCH_GROUP.join(pitch.describe_pitches() for pitch in self.headword_accents)

    def has_pitch(self) -> bool:
        return bool(self.headword_accents and all(token.has_accent() for token in self.headword_accents))
