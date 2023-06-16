# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Data source:
# https://raw.githubusercontent.com/mifunetoshiro/kanjium/master/data/source_files/raw/accents.txt

import re
from typing import Iterable, Collection

try:
    from .common import *
    from ..mecab_controller.kana_conv import to_katakana, kana_to_moras
except ImportError:
    from common import *
    from mecab_controller.kana_conv import to_katakana, kana_to_moras


def search_pitch_accent_numbers(accents: str):
    if accents.strip() == NO_ACCENT:
        return NO_ACCENT
    return {int(re.search(r'\d{1,2}$', pos).group()) for pos in accents.split(',')}


class AccentEntry:
    """ Represents an entry in kanjium_data.tsv """

    def __init__(self, keyword: str, reading: str, accents: str):
        self._keyword = keyword
        self._reading = kana_to_moras(to_katakana(reading or keyword))
        self._accents = search_pitch_accent_numbers(accents)

    @property
    def keyword(self) -> str:
        return self._keyword

    @property
    def moraes(self) -> list[str]:
        return self._reading

    @property
    def accents(self) -> Iterable[int]:
        if not self.has_accent():
            raise ValueError("This entry has no accent.")
        return self._accents

    def has_accent(self):
        return self._accents != NO_ACCENT


def format_entry(moraes: list[str], accent: int) -> str:
    """ Format an entry from the data in the original pitch accents file to something that uses html """

    result = []
    overline_flag = False

    for idx, morae in enumerate(moraes):
        # Start or end overline when necessary
        if not overline_flag and ((idx == 1 and (accent == 0 or accent > 1)) or (idx == 0 and accent == 1)):
            result.append('<span class="overline">')
            overline_flag = True

        result.append(morae)

        if overline_flag and idx == accent - 1:
            result.append('</span>&#42780;')
            overline_flag = False

    # Close the overline if it's still open
    if overline_flag:
        result.append("</span>")

    return ''.join(result)


def create_formatted(entry: AccentEntry) -> Collection[FormattedEntry]:
    if entry.has_accent():
        return dict.fromkeys(
            FormattedEntry(
                katakana_reading=''.join(entry.moraes),
                html_notation=format_entry(entry.moraes, int(pitch_num)),
                pitch_number=str(pitch_num),
            )
            for pitch_num in entry.accents
        )
    else:
        return {
            FormattedEntry(
                katakana_reading=''.join(entry.moraes),
                html_notation=''.join(entry.moraes),
                pitch_number=NO_ACCENT,
            ): None
        }


class KanjiumDb(AccDbManager):
    _source_csv_path = None
    _formatted_csv_path = os.path.join(RES_DIR_PATH, "kanjium_formatted.csv")

    def read_entries(self) -> Iterable[AccentEntry]:
        with open(self._source_csv_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield AccentEntry(*line.split('\t'))

    def create_derivative(self) -> AccentDict:
        """ Build the derived pitch accents file from the original pitch accents file and save it as *.csv """
        temp_dict = {}
        for entry in self.read_entries():
            temp_dict.setdefault(entry.keyword, dict()).update(create_formatted(entry))
        return AccentDict(temp_dict)


if __name__ == '__main__':
    KanjiumDb.test()
