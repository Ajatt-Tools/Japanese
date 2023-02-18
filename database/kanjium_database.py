# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Data source:
# https://raw.githubusercontent.com/mifunetoshiro/kanjium/master/data/source_files/raw/accents.txt

from typing import Iterable

try:
    from .common import *
    from ..mecab_controller import to_katakana
except ImportError:
    from common import *
    from mecab_controller import to_katakana


class AccentEntry:
    """ Represents an entry in kanjium_data.tsv """

    def __init__(self, keyword: str, reading: str, accents: str):
        self._keyword = keyword
        self._reading = kana_to_moras(to_katakana(reading or keyword))
        self._accents = {int(re.search(r'\d{1,2}$', pos).group()) for pos in accents.split(',')}

    @property
    def keyword(self) -> str:
        return self._keyword

    @property
    def moraes(self) -> List[str]:
        return self._reading

    @property
    def accents(self) -> Iterable[int]:
        return self._accents


def format_entry(moraes: List[str], accent: int) -> str:
    """ Format an entry from the data in the original database to something that uses html """

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


class KanjiumDb(AccDbManager):
    accent_database = os.path.join(DB_DIR_PATH, "kanjium_data.tsv")
    derivative_database = os.path.join(DB_DIR_PATH, "kanjium_pronunciation.csv")

    def create_derivative(self) -> AccentDict:
        """ Build the derived database from the original database and save it as *.csv """
        temp_dict: AccentDict = {}

        with open(self.accent_database, encoding="utf-8") as f:
            entries = [AccentEntry(*line.split('\t')) for line in f]

        for entry in entries:
            for pitch_num in entry.accents:
                value = FormattedEntry(''.join(entry.moraes), format_entry(entry.moraes, pitch_num), str(pitch_num))
                temp_dict.setdefault(entry.keyword, [])
                if value not in temp_dict[entry.keyword]:
                    temp_dict[entry.keyword].append(value)

        return temp_dict


if __name__ == '__main__':
    KanjiumDb.test()
