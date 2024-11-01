# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import csv
import enum
import os
import pathlib
import re
import typing
from collections.abc import Iterable, Sequence
from typing import NamedTuple, NewType

from .consts import NO_ACCENT, PITCH_DIR_PATH

Stored = typing.TypeVar("Stored")

RE_PITCH_NUM = re.compile(r"\d+|\?")
RE_PITCH_TAG = re.compile(r"(<[^<>]+>)")


class AccDictRawTSVEntry(typing.TypedDict):
    """Entry as it appears in the pitch accents file."""

    headword: str
    katakana_reading: str
    html_notation: str
    pitch_number: str  # can't be converted to int. might contain separators and special symbols.
    frequency: str  # must be converted to int. larger number => more occurrences.


class AccDictProvider:
    bundled = "bundled"
    user = "user"


class FormattedEntry(NamedTuple):
    katakana_reading: str
    html_notation: str
    pitch_number: str

    def has_accent(self) -> bool:
        return self.pitch_number != NO_ACCENT

    @property
    def pitch_number_html(self):
        return f'<span class="pitch_number">{self.pitch_number}</span>'


AccentDict = dict[str, list[FormattedEntry]]


class OrderedSet(collections.OrderedDict, typing.Sequence[Stored]):
    def __init__(self, iterable: typing.Optional[Iterable[Stored]] = None) -> None:
        super().__init__()
        if iterable is not None:
            self.update(self.fromkeys(iterable))

    def add(self, value: Stored):
        self[value] = None


def is_dunder(name: str) -> bool:
    """Returns whether name is a dunder name."""
    return name.startswith("__") and name.endswith("__")


def files_in_dir(dir_path: pathlib.Path) -> Iterable[str]:
    if not dir_path.is_dir():
        raise ValueError(f"not a directory: {dir_path}")
    return (
        os.path.normpath(os.path.join(root, file))
        for root, dirs, files in os.walk(dir_path)
        if is_dunder(os.path.basename(root)) is False
        for file in files
    )


def split_pitch_numbers(s: str) -> list[str]:
    return re.findall(RE_PITCH_NUM, s)


def nakaten_separated_katakana_reading(html_notation: str) -> str:
    """
    In some (rare) cases (in the NHK accent dictionary),
    a word consists of multiple words, and the parts are separated with a `・`.
    E.g., 起死回生 = キシ・カイセイ(1+0) or キシ・カイセイ(2+0)
    The boundaries are lost in the katakana reading, but are retained in the html notation.
    The information is needed to correctly draw downstep graphs from JS code.
    """
    return re.sub(RE_PITCH_TAG, "", html_notation).replace("°", "゚")


def split_html_notation(html_notation: str) -> Iterable[str]:
    return filter(bool, map(str.strip, re.split(RE_PITCH_TAG, html_notation)))


def get_tsv_reader(f: typing.Iterable[str]) -> csv.DictReader:
    """
    Prepare a reader to load the accent dictionary.
    Keys are already included in the csv file.
    """
    return csv.DictReader(
        f,
        dialect="excel-tab",
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )
