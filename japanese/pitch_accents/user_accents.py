# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import os
from collections.abc import MutableMapping, Iterable, Sequence
from typing import Union, NamedTuple

from .common import FormattedEntry, AccentDict
from .consts import NO_ACCENT
from .format_accents import format_entry
from ..helpers.file_ops import touch, user_files_dir
from ..mecab_controller.kana_conv import kana_to_moras, to_katakana


def search_pitch_accent_numbers(accents: str) -> Iterable[Union[str, int]]:
    return ((int(pos) if pos != NO_ACCENT else NO_ACCENT) for pos in accents.split(","))


class AccentEntry(NamedTuple):
    """Represents a parsed entry in the user TSV file."""

    headword: str
    moras: tuple[str, ...]
    accents: tuple[Union[str, int], ...]

    def has_accent(self):
        return self.accents != NO_ACCENT

    @classmethod
    def from_csv_line(cls, line: str):
        headword, reading, accents = line.split("\t")
        return cls(
            headword=headword,
            moras=tuple(kana_to_moras(to_katakana(reading or headword))),
            accents=tuple(dict.fromkeys(search_pitch_accent_numbers(accents))),
        )


def create_formatted(entry: AccentEntry) -> MutableMapping[FormattedEntry, None]:
    return dict.fromkeys(
        FormattedEntry(
            katakana_reading="".join(entry.moras),
            html_notation=format_entry(entry.moras, pitch_num),
            pitch_number=str(pitch_num),
        )
        for pitch_num in entry.accents
    )


class UserAccentData:
    source_csv_path = os.path.join(user_files_dir(), "user_data.tsv")

    def __init__(self):
        self.self_check()

    def self_check(self):
        if not os.path.isfile(self.source_csv_path):
            touch(self.source_csv_path)
            print(f"Created file: {self.source_csv_path}")

    def read_entries(self) -> Iterable[AccentEntry]:
        with open(self.source_csv_path, encoding="utf-8") as f:
            for line in f:
                if line := line.strip():
                    yield AccentEntry.from_csv_line(line)

    def create_formatted(self) -> AccentDict:
        """Build the derived pitch accents file from the original pitch accents file and save it as *.csv"""
        temp_dict = collections.defaultdict(dict)
        for entry in self.read_entries():
            temp_dict[entry.headword].update(create_formatted(entry))
        for key in temp_dict:
            temp_dict[key] = tuple(temp_dict[key])
        return AccentDict(temp_dict)


# Debug
##########################################################################


def main():
    data = UserAccentData()
    formatted = data.create_formatted()
    for key, value in formatted.items():
        print(f"{key=}; {value=}")


if __name__ == "__main__":
    main()
