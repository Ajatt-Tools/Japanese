# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
from collections.abc import Sequence
from typing import NamedTuple

try:
    from .common import split_pitch_numbers, FormattedEntry
    from .consts import NO_ACCENT
    from ..mecab_controller.kana_conv import to_hiragana, kana_to_moras
    from ..mecab_controller.basic_types import MecabParsedToken
except ImportError:
    from common import split_pitch_numbers, FormattedEntry
    from consts import NO_ACCENT
    from mecab_controller.kana_conv import to_hiragana, kana_to_moras
    from mecab_controller.basic_types import MecabParsedToken

SEP_PITCH_TYPES = ','
SEP_PITCH_GROUP = ' '
SEP_TYPE_NUM = ':'


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
            return f"{self.type.name}{SEP_TYPE_NUM}{self.number}"
        else:
            return self.type.name


class PitchAccentEntry(NamedTuple):
    katakana_reading: str
    pitches: list[PitchParam]

    def has_accent(self) -> bool:
        return bool(self.pitches and any(pitch.type != PitchType.unknown for pitch in self.pitches))

    def describe_pitches(self) -> str:
        return SEP_PITCH_TYPES.join(pitch.describe() for pitch in self.pitches)

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


def main():
    from mecab_controller.basic_types import PartOfSpeech, Inflection

    entry = PitchAccentEntry.from_formatted(FormattedEntry(
        katakana_reading="たのしい",
        pitch_number="3",
        html_notation=""
    ))

    token = AccDbParsedToken(
        word="楽しかった",
        headword="楽しい",
        katakana_reading="たのしかった",
        part_of_speech=PartOfSpeech.unknown,
        inflection_type=Inflection.unknown,
        headword_accents=(entry,),
    )

    assert token.describe_pitches() == "nakadaka:3"


if __name__ == '__main__':
    main()
