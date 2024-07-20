# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import csv
import pathlib
import typing
from collections.abc import Iterable

from ..mecab_controller.kana_conv import kana_to_moras, to_katakana
from .basic_types import SEP_PITCH_TYPES
from .common import (
    AccDictRawTSVEntry,
    AccentDict,
    FormattedEntry,
    OrderedSet,
    repack_accent_dict,
)
from .consts import NO_ACCENT, USER_DATA_CSV_PATH
from .format_accents import format_entry


class UserAccDictRawTSVEntry(typing.TypedDict):
    """Entry as it appears in the user's pitch accents file."""

    headword: str
    katakana_reading: str
    pitch_numbers: str


def get_user_tsv_reader(f: typing.Iterable[str]) -> csv.DictReader:
    """
    Prepare a reader to load the accent dictionary.
    Keys are described in the typed dict.
    """
    return csv.DictReader(
        f,
        dialect="excel-tab",
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
        fieldnames=UserAccDictRawTSVEntry.__annotations__,
    )


def read_user_tsv_entries(tsv_file_path: pathlib.Path) -> Iterable[UserAccDictRawTSVEntry]:
    row_dict: UserAccDictRawTSVEntry
    try:
        with open(tsv_file_path, newline="", encoding="utf-8") as f:
            for row_dict in get_user_tsv_reader(f):
                row_dict["headword"] = to_katakana(row_dict["headword"])
                row_dict["katakana_reading"] = to_katakana(row_dict["katakana_reading"] or row_dict["headword"])
                yield row_dict
    except FileNotFoundError:
        pass


def parse_pitch_number(pos: str) -> typing.Union[str, int]:
    return int(pos) if pos != NO_ACCENT else NO_ACCENT


def split_pitch_numbers(pitch_nums_as_str: str) -> Iterable[typing.Union[str, int]]:
    return dict.fromkeys(parse_pitch_number(pos) for pos in pitch_nums_as_str.split(SEP_PITCH_TYPES))


def formatted_from_tsv_row(row_dict: UserAccDictRawTSVEntry) -> typing.Sequence[FormattedEntry]:
    row_dict["katakana_reading"] = to_katakana(row_dict["katakana_reading"])
    return dict.fromkeys(
        FormattedEntry(
            katakana_reading=row_dict["katakana_reading"],
            html_notation=format_entry(kana_to_moras(row_dict["katakana_reading"]), pitch_num),
            pitch_number=str(pitch_num),
        )
        for pitch_num in split_pitch_numbers(row_dict["pitch_numbers"])
    )


def iter_user_formatted_rows(tsv_file_path: pathlib.Path) -> typing.Iterable[AccDictRawTSVEntry]:
    formatted: FormattedEntry
    for row_dict in read_user_tsv_entries(tsv_file_path):
        for formatted in formatted_from_tsv_row(row_dict):
            yield AccDictRawTSVEntry(
                headword=row_dict["headword"],
                katakana_reading=formatted.katakana_reading,
                html_notation=formatted.html_notation,
                pitch_number=formatted.pitch_number,
                frequency="0",
            )


def create_user_formatted_accents() -> AccentDict:
    """Build the derived pitch accents file from the original pitch accents file and save it as *.csv"""
    temp_dict: dict[str, OrderedSet[FormattedEntry]] = collections.defaultdict(OrderedSet)
    for row_dict in read_user_tsv_entries(USER_DATA_CSV_PATH):
        temp_dict[row_dict["headword"]].update(formatted_from_tsv_row(row_dict))
    return repack_accent_dict(temp_dict)
