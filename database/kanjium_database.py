# Pitch Accent add-on for Anki 2.1
# Copyright (C) 2021  Ren Tatsumoto. <tatsu at autistici.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Any modifications to this file must keep this entire header intact.

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
        self._reading = kana_to_moraes(to_katakana(reading or keyword))
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

    def build_derivative(self) -> None:
        """ Build the derived database from the original database and save it as *.csv """
        with open(self.accent_database, encoding="utf-8") as f:
            entries = [AccentEntry(*line.split('\t')) for line in f]

        for entry in entries:
            for pitch_num in entry.accents:
                value = FormattedEntry(''.join(entry.moraes), format_entry(entry.moraes, pitch_num), pitch_num)
                self._temp_dict.setdefault(entry.keyword, [])
                if value not in self._temp_dict[entry.keyword]:
                    self._temp_dict[entry.keyword].append(value)

        self.save_derivative()


if __name__ == '__main__':
    KanjiumDb.test()
