# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
from collections import UserList
from typing import Optional, Iterable, Sequence

try:
    from .common import split_pitch_numbers
    from .consts import NO_ACCENT
    from ..mecab_controller.kana_conv import to_hiragana, kana_to_moras
    from ..mecab_controller.basic_types import MecabParsedToken
except ImportError:
    from common import split_pitch_numbers
    from consts import NO_ACCENT
    from mecab_controller.kana_conv import to_hiragana, kana_to_moras
    from mecab_controller.basic_types import MecabParsedToken

SEP_PITCH_TYPES = ','
SEP_PITCH_GROUP = ' '


class PitchType(enum.Enum):
    unknown = NO_ACCENT
    heiban = 0
    atamadaka = 1
    nakadaka = object()
    odaka = object()


@dataclasses.dataclass(frozen=True)
class AccDbParsedToken(MecabParsedToken):
    """
    Add pitch number to the parsed token
    """
    headword_katakana_reading: Optional[str] = None
    pitch_number: str = NO_ACCENT

    def is_inflected(self):
        return self.katakana_reading != self.headword_katakana_reading

    @property
    def hiragana_reading(self) -> str:
        return to_hiragana(self.katakana_reading)

    @property
    def pitch_pattern_type(self) -> Sequence[PitchType]:
        """
        Return pitch accent type.
        Pitch number is stored as a string in the pitch accents CSV file.
        The string can either be directly convertible to int, indicate that the pitch is unknown,
        or contain more than one number.
        """
        accents: list[PitchType] = []
        for symbol in split_pitch_numbers(self.pitch_number):
            try:
                pitch_num = int(symbol)
            except ValueError:
                accents.append(PitchType.unknown)
                continue
            try:
                accents.append(PitchType(pitch_num))
            except ValueError:
                if not self.headword_katakana_reading:
                    raise ValueError("headword's katakana readings was not provided.")
                accents.append(
                    PitchType.odaka
                    if len(kana_to_moras(self.headword_katakana_reading)) == int(pitch_num)
                    else PitchType.nakadaka
                )
                continue
        return accents

    @property
    def pitch_pattern_type_formatted(self) -> str:
        return SEP_PITCH_TYPES.join(pitch_type.name for pitch_type in self.pitch_pattern_type)


class AccDbParsedTokenCol(UserList[AccDbParsedToken]):
    def __init__(self, init_list: Optional[Iterable[AccDbParsedToken]] = None, *, word: Optional[str] = None):
        super().__init__(init_list)
        self.word = (word or self[0].word)

    @property
    def katakana_readings(self) -> Iterable[str]:
        return (token.katakana_reading for token in self)

    @property
    def hiragana_readings(self) -> Iterable[str]:
        return (token.hiragana_reading for token in self)

    @property
    def pitch_types_formatted(self) -> str:
        return SEP_PITCH_GROUP.join(token.pitch_pattern_type_formatted for token in self)

    @property
    def pitch_numbers(self) -> str:
        return SEP_PITCH_GROUP.join(token.pitch_number for token in self)

    @property
    def parts_of_speech(self) -> str:
        return SEP_PITCH_GROUP.join(token.part_of_speech.name for token in self)


def main():
    from mecab_controller.basic_types import PartOfSpeech, Inflection
    token = AccDbParsedToken(
        word="楽しかった",
        headword="楽しい",
        katakana_reading="たのしかった",
        part_of_speech=PartOfSpeech.unknown,
        inflection_type=Inflection.unknown,
        pitch_number="3",
        headword_katakana_reading="たのしい"
    )
    assert token.pitch_pattern_type == [PitchType.nakadaka, ]


if __name__ == '__main__':
    main()
