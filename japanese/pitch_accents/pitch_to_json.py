# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import io
import json
import typing

from .common import FormattedEntry, replace_degree_with_dakuten
from .entry_to_moras import (
    Mora,
    MoraFlag,
    MoraSequence,
    PitchLevel,
    Quark,
    entry_to_moras,
)


class MoraOutputJson(typing.TypedDict):
    txt: str
    level: str
    flags: list[str]


class MoraSequenceOutputJson(typing.TypedDict):
    moras: list[MoraOutputJson]
    pitch_number: str
    pitch_type: str
    raw_headword: str
    katakana_reading: str


@dataclasses.dataclass
class MoraCombined:
    txt: str
    flags: MoraFlag
    level: PitchLevel


def combine_mora(mora: Mora) -> MoraCombined:
    symbols_txt = io.StringIO()
    flags = mora.flags
    for symbol in mora.txt:
        if isinstance(symbol, str):
            symbols_txt.write(symbol)
        elif isinstance(symbol, Quark):
            symbols_txt.write(replace_degree_with_dakuten(symbol.txt))
            flags |= symbol.flags
        else:
            raise ValueError(f"unknown type: {type(symbol)}")
    return MoraCombined(symbols_txt.getvalue(), flags=flags, level=mora.level)


def mora_to_dict(mora: MoraCombined) -> MoraOutputJson:
    return {
        "txt": mora.txt,
        "level": mora.level.name,
        "flags": [flag.name for flag in MoraFlag if flag in mora.flags],
    }


def mora_sequence_to_dict(seq: MoraSequence) -> MoraSequenceOutputJson:
    return {
        "raw_headword": seq.entry.raw_headword,
        "katakana_reading": seq.entry.katakana_reading,
        "pitch_number": seq.entry.pitch_number,
        "pitch_type": seq.pitch_type.name,
        "moras": [mora_to_dict(combine_mora(mora)) for mora in seq.moras if not mora.is_trailing()],
    }


def make_json_from_entry(entry: FormattedEntry) -> MoraSequenceOutputJson:
    return mora_sequence_to_dict(entry_to_moras(entry, enable_trailing_mora=False))
