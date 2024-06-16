# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import os
from collections.abc import Iterable, MutableMapping
from typing import NamedTuple, Union

from ..helpers.file_ops import touch, user_files_dir
from ..mecab_controller.kana_conv import kana_to_moras, to_katakana
from .common import AccentDict, FormattedEntry, OrderedSet, repack_accent_dict
from .consts import NO_ACCENT
from .format_accents import format_entry

USER_DATA_CSV_PATH = os.path.join(user_files_dir(), "user_data.tsv")


def search_pitch_accent_numbers(accents: str) -> Iterable[Union[str, int]]:
    return ((int(pos) if pos != NO_ACCENT else NO_ACCENT) for pos in accents.split(","))


class TSVAccentEntry(NamedTuple):
    """Represents a parsed entry in the user TSV file."""

    headword: str
    moras: tuple[str, ...]
    accents: tuple[Union[str, int], ...]
    katakana_reading: str

    def has_accent(self):
        return self.accents != NO_ACCENT

    @classmethod
    def from_csv_line(cls, line: str):
        headword, reading, accents = line.split("\t")
        reading = to_katakana(reading or headword)
        return cls(
            headword=headword,
            moras=tuple(kana_to_moras(reading)),
            accents=tuple(dict.fromkeys(search_pitch_accent_numbers(accents))),
            katakana_reading=reading,
        )


def create_formatted(entry: TSVAccentEntry) -> OrderedSet[FormattedEntry]:
    return OrderedSet.fromkeys(
        FormattedEntry(
            katakana_reading=entry.katakana_reading,
            html_notation=format_entry(entry.moras, pitch_num),
            pitch_number=str(pitch_num),
        )
        for pitch_num in entry.accents
    )


class UserAccentData:
    source_csv_path: str = USER_DATA_CSV_PATH  # accessed by the settings dialog

    def __init__(self):
        self._self_check()

    def _self_check(self):
        if not os.path.isfile(self.source_csv_path):
            touch(self.source_csv_path)
            print(f"Created file: {self.source_csv_path}")

    def _read_entries(self) -> Iterable[TSVAccentEntry]:
        with open(self.source_csv_path, newline="", encoding="utf-8") as f:
            for line in f:
                if line := line.strip():
                    yield TSVAccentEntry.from_csv_line(line)

    def create_formatted(self) -> AccentDict:
        """Build the derived pitch accents file from the original pitch accents file and save it as *.csv"""
        temp_dict: dict[str, OrderedSet[FormattedEntry]] = collections.defaultdict(OrderedSet)
        for entry in self._read_entries():
            temp_dict[to_katakana(entry.headword)].update(create_formatted(entry))
        return repack_accent_dict(temp_dict)
