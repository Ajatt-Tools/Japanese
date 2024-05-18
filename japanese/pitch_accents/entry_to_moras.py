# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import html
import re
from typing import Optional
from collections.abc import Iterable

from .common import FormattedEntry
from .styles import XmlTags
from ..mecab_controller import kana_to_moras

RE_PITCH_TAG = re.compile(r"(<[^<>]+>)")


def split_html_notation(entry: FormattedEntry) -> Iterable[str]:
    return filter(bool, map(str.strip, re.split(RE_PITCH_TAG, entry.html_notation)))


@enum.unique
class PitchLevel(enum.Enum):
    low = "low"
    high = "high"


class MoraFlag(enum.Flag):
    nasal = enum.auto()
    devoiced = enum.auto()


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


class SpecialSymbols:
    nasal_dakuten_esc = "&#176;"  # ° is used in the NHK dictionary before カ, etc.
    nasal_dakuten = html.unescape("&#176;")
    nakaten = "・"


def entry_to_moras(entry: FormattedEntry) -> list[Mora]:
    moras: list[Mora] = []
    current_level: PitchLevel = PitchLevel.low
    current_flags = MoraFlag(0)

    for token in split_html_notation(entry):
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
    return moras


def mora_flags_to_classname(flags: MoraFlag):
    return " ".join(flag.name for flag in MoraFlag if flag in flags)
