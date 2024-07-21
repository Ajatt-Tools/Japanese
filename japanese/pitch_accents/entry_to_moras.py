# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import html
import typing
from typing import Optional

from ..mecab_controller import kana_to_moras
from .basic_types import PitchType, pitch_type_from_pitch_num
from .common import FormattedEntry, split_html_notation
from .styles import XmlTags


@enum.unique
class PitchLevel(enum.Enum):
    low = "low"
    high = "high"


@enum.unique
class MoraFlag(enum.Flag):
    nasal = enum.auto()
    devoiced = enum.auto()
    trailing = enum.auto()


@dataclasses.dataclass
class Quark:
    txt: str
    flags: MoraFlag


@dataclasses.dataclass
class Mora:
    txt: str
    level: PitchLevel
    flags: MoraFlag
    quark: Optional[Quark] = None

    def is_trailing(self) -> bool:
        if MoraFlag.trailing in self.flags:
            assert not self.txt
            return True
        return False


class SpecialSymbols:
    nasal_dakuten_esc = "&#176;"  # ° is used in the NHK dictionary before カ, etc.
    nasal_dakuten = html.unescape("&#176;")
    nakaten = "・"


class MoraSequence(typing.NamedTuple):
    moras: list[Mora]
    pitch_type: PitchType
    entry: FormattedEntry


def entry_to_moras(entry: FormattedEntry) -> MoraSequence:
    moras: list[Mora] = []
    current_level: PitchLevel = PitchLevel.low
    current_flags = MoraFlag(0)

    for token in split_html_notation(html_notation):
        if token in (XmlTags.low_rise_start, XmlTags.low_start, XmlTags.high_drop_end, XmlTags.high_end):
            current_level = PitchLevel.low
        elif token in (XmlTags.high_start, XmlTags.high_drop_start, XmlTags.low_rise_end, XmlTags.low_end):
            current_level = PitchLevel.high
        elif token == XmlTags.nasal_start:
            current_flags |= MoraFlag.nasal
        elif token == XmlTags.nasal_end:
            current_flags &= ~MoraFlag.nasal
        elif token == XmlTags.devoiced_start:
            current_flags |= MoraFlag.devoiced
        elif token == XmlTags.devoiced_end:
            current_flags &= ~MoraFlag.devoiced
        elif token in (XmlTags.handakuten_start, XmlTags.handakuten_end):
            pass
        elif token in (SpecialSymbols.nasal_dakuten_esc, SpecialSymbols.nasal_dakuten):
            assert MoraFlag.nasal in current_flags, "nasal handakuten only appears inside nasal tags."
            assert len(moras) > 0, "nasal handakuten must be attached to an existing mora."
            moras[-1].quark = Quark(token, flags=current_flags)
        elif token == SpecialSymbols.nakaten:
            # Skip nakaten because it's not a mora.
            # In NHK-1998, nakaten is used to separate parts of words
            # that consist of multiple sub-words, e.g. 二十四時間.
            pass
        else:
            assert token.isalpha(), f"can't proceed: {entry}"
            moras.extend(Mora(mora, current_level, flags=current_flags) for mora in kana_to_moras(token))

    pitch_type = pitch_type_from_pitch_num(entry.pitch_number, len(moras))
    if pitch_type == PitchType.heiban or len(moras) == 1:
        assert pitch_type in (PitchType.heiban, PitchType.atamadaka)
        level = PitchLevel.high if pitch_type == PitchType.heiban else PitchLevel.low
        moras.append(Mora(txt="", level=level, flags=MoraFlag.trailing))

    return MoraSequence(moras=moras, pitch_type=pitch_type, entry=entry)


def mora_flags2class_name(flags: MoraFlag):
    return " ".join(flag.name for flag in MoraFlag if flag.name and flag in flags)
