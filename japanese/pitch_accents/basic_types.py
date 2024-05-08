# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
from collections.abc import Sequence
from typing import NamedTuple

from ..mecab_controller.basic_types import MecabParsedToken
from ..mecab_controller.kana_conv import kana_to_moras
from .common import FormattedEntry, split_pitch_numbers
from .consts import NO_ACCENT

SEP_PITCH_GROUP = " "
SEP_PITCH_TYPES = ","
SEP_READING_PITCH = ":"
SEP_PITCH_TYPE_NUM = "-"


class PitchType(enum.Enum):
    unknown = NO_ACCENT
    heiban = 0
    atamadaka = 1
    nakadaka = object()
    odaka = object()


class PitchParam(NamedTuple):
    type: PitchType
    number: str

    def describe(self):
        if self.type == PitchType.nakadaka:
            return f"{self.type.name}{SEP_PITCH_TYPE_NUM}{self.number}"
        else:
            return self.type.name


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
    def from_formatted(cls, entry: FormattedEntry):
        """
        Construct cls from a dictionary entry.

        Pitch number is stored as a string in the pitch accents CSV file.
        The string can either be directly convertible to int, indicate that the pitch is unknown,
        or contain more than one number.
        """
        pitches: list[PitchParam] = []

        for symbol in split_pitch_numbers(entry.pitch_number):
            try:
                pitch_num = int(symbol)
            except ValueError:
                # pitch num is not a number => pitch is unknown
                pitches.append(PitchParam(PitchType.unknown, symbol))
                continue
            try:
                pitches.append(PitchParam(PitchType(pitch_num), symbol))
            except ValueError:
                # either nakadaka or odaka
                pitches.append(
                    PitchParam(PitchType.odaka, symbol)
                    if len(kana_to_moras(entry.katakana_reading)) == int(pitch_num)
                    else PitchParam(PitchType.nakadaka, symbol)
                )
                continue
        return cls(
            katakana_reading=entry.katakana_reading,
            pitches=pitches,
        )


@dataclasses.dataclass(frozen=True)
class AccDbParsedToken(MecabParsedToken):
    """
    Add pitch number to the parsed token
    """

    headword_accents: Sequence[PitchAccentEntry]

    def describe_pitches(self) -> str:
        return SEP_PITCH_GROUP.join(pitch.describe_pitches() for pitch in self.headword_accents)

    def has_pitch(self) -> bool:
        return all(token.has_accent() for token in self.headword_accents)
