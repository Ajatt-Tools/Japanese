# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
from collections.abc import MutableSequence, Sequence
from typing import NamedTuple

from ..mecab_controller import to_hiragana
from ..mecab_controller.basic_types import MecabParsedToken, PartOfSpeech
from .common import (
    FormattedEntry,
    nakaten_separated_katakana_reading,
    split_pitch_numbers,
)
from .consts import NO_ACCENT

SEP_PITCH_GROUP = " "
SEP_PITCH_TYPES = ","
SEP_READING_PITCH = ":"
SEP_PITCH_TYPE_NUM = "-"
SMALL_KANA_CHARS = "ァィゥェォャュョぁぃぅぇぉゃゅょ"


@enum.unique
class PitchType(enum.Enum):
    unknown = NO_ACCENT
    heiban = 0
    atamadaka = 1
    nakadaka = object()
    odaka = object()
    kifuku = object()


@enum.unique
class PitchUnknown(enum.Enum):
    many = enum.auto()
    none = enum.auto()


def pitch_type_from_pitch_num(pitch_num_as_str: str, n_moras: int) -> PitchType:
    if not pitch_num_as_str:
        return PitchType.unknown

    try:
        pitch_num = int(pitch_num_as_str)
    except ValueError:
        # pitch num is not a number => pitch is unknown
        return PitchType.unknown

    if pitch_num < 0:
        raise ValueError("pitch number can't be less than 0")
    if n_moras < 1:
        raise ValueError("word must consist of at least 1 mora")
    if pitch_num > n_moras:
        raise ValueError("pitch must drop inside the word or right after")

    if pitch_num == 0:
        return PitchType.heiban
    if pitch_num == 1:
        return PitchType.atamadaka
    if pitch_num == n_moras:
        return PitchType.odaka
    if pitch_num < n_moras:
        return PitchType.nakadaka
    return PitchType.unknown


def count_moras(katakana_reading: str) -> int:
    return sum(1 for char in katakana_reading if char not in SMALL_KANA_CHARS)


def is_verb_or_i_adjective(part_of_speech: PartOfSpeech) -> bool:
    assert isinstance(part_of_speech, PartOfSpeech), f"expected PartOfSpeech, got {type(part_of_speech)}"
    return part_of_speech in (PartOfSpeech.verb, PartOfSpeech.i_adjective)


def adjust_if_kifuku(part_of_speech: PartOfSpeech, pitch_type: PitchType) -> PitchType:
    """
    non-heiban verbs and i-adjectives are commonly referred to as kifuku.
    """
    assert isinstance(pitch_type, PitchType), f"expected PitchType, got {type(pitch_type)}"
    if (
        pitch_type
        and is_verb_or_i_adjective(part_of_speech)
        and pitch_type not in (PitchType.heiban, PitchType.unknown)
    ):
        return PitchType.kifuku
    return pitch_type


class PitchParam(NamedTuple):
    type: PitchType
    number: str
    n_moras: int

    def describe(self):
        """
        Returns pattern name if not nakadaka: unknown, heiban, atamadaka, odaka, kifuku.
        Otherwise, returns pattern + pitch number: nakadaka-2, nakadaka-3, etc.
        """
        if self.type in (PitchType.nakadaka, PitchType.kifuku):
            # kifuku can be atamadaka, nakadaka or odaka.
            # always print its pitch number to help the JS script figure out how to draw the pitch graph.
            return f"{self.type.name}{SEP_PITCH_TYPE_NUM}{self.number}"
        else:
            return self.type.name

    @classmethod
    def from_symbol(cls, katakana_reading: str, pitch_num_as_str: str, part_of_speech: PartOfSpeech):
        n_moras = count_moras(katakana_reading)
        return cls(
            type=adjust_if_kifuku(part_of_speech, pitch_type_from_pitch_num(pitch_num_as_str, n_moras=n_moras)),
            number=pitch_num_as_str,
            n_moras=n_moras,
        )


class PitchAccentEntry(NamedTuple):
    katakana_reading: str
    katakana_reading_sep: str
    pitches: list[PitchParam]

    def has_accent(self) -> bool:
        return bool(self.pitches and any(pitch.type != PitchType.unknown for pitch in self.pitches))

    def describe_pitches(self, use_hiragana: bool = False) -> str:
        """
        Returns reading and its pitch accents, separated by a colon.
        Examples:
            コウソクドウロ:nakadaka-5
            メイワク:atamadaka
            キシ・カイセイ:nakadaka-2,heiban (the first part of the word is 2, the second part is 0)
        """
        if use_hiragana:
            reading = to_hiragana(self.katakana_reading_sep)
        else:
            reading = self.katakana_reading_sep
        return reading + SEP_READING_PITCH + SEP_PITCH_TYPES.join(pitch.describe() for pitch in self.pitches)

    @classmethod
    def from_formatted(cls, entry: FormattedEntry, part_of_speech: PartOfSpeech) -> "PitchAccentEntry":
        """
        Construct cls from a dictionary entry.

        Pitch number is stored as a string in the pitch accents CSV file.
        The string can either be directly convertible to int, indicate that the pitch is unknown,
        or contain more than one number.
        """
        return cls(
            katakana_reading=entry.katakana_reading,
            katakana_reading_sep=nakaten_separated_katakana_reading(entry.html_notation),
            pitches=[
                PitchParam.from_symbol(entry.katakana_reading, symbol, part_of_speech)
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

    def describe_pitches(self, maximum_pitch_accents: int = 99, use_hiragana: bool = False) -> str:
        """
        Returns readings in this format: reading1:pitch_type reading2:pitch_type
        Args:
            maximum_pitch_accents: Limit number of pitches to print.
            use_hiragana: Print text in hiragana.
        Examples:
            コッキョウ:heiban クニザカイ:nakadaka-3 (one word has two different readings, with their accents listed)
            マンビキ:heiban マンビキ:odaka (one word has two possible accents)
        """
        return SEP_PITCH_GROUP.join(
            pitch.describe_pitches(use_hiragana) for pitch in self.headword_accents[:maximum_pitch_accents]
        )

    def has_pitch(self) -> bool:
        return bool(self.headword_accents and all(token.has_accent() for token in self.headword_accents))

    @classmethod
    def from_mecab_parsed(
        cls, mpt: MecabParsedToken, headword_accents: Sequence[PitchAccentEntry]
    ) -> "AccDbParsedToken":
        return cls(
            **dataclasses.asdict(mpt),
            headword_accents=headword_accents,
        )
