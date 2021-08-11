# -*- coding: utf-8 -*-

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

import re
from typing import Iterable

try:
    from .common import *
    from ..mecab_controller import to_katakana
except ImportError:
    from common import *
    from mecab_controller import to_katakana


def kana_to_moraes(kana: str) -> List[str]:
    return re.findall(r'.[ャュョゃゅょ]?', kana)


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
            result += '<span class="overline">'
            overline_flag = True
        if overline_flag and idx == accent:
            result += '</span>&#42780;'
            overline_flag = False

        result += morae

    # Close the overline if it's still open
    if overline_flag:
        result += "</span>"

    return ''.join(result)


class KanjiumDb(AccDbManager):
    accent_database = os.path.join(DB_DIR_PATH, "kanjium_data.tsv")
    derivative_database = os.path.join(DB_DIR_PATH, "kanjium_pronunciation.csv")

    @classmethod
    def build_derivative(cls, dest_path: str = derivative_database) -> None:
        """ Build the derived database from the original database and save it as *.csv """
        temp_dict = {}

        with open(cls.accent_database, 'r', encoding="utf-8") as f:
            entries = [AccentEntry(*line.split('\t')) for line in f]

        for entry in entries:
            for accent in entry.accents:
                # A tuple holding both the spelling in katakana, and the katakana with pitch/accent markup
                value = (''.join(entry.moraes), format_entry(entry.moraes, accent))

                # Add expressions to dict
                temp_dict[entry.keyword] = temp_dict.get(entry.keyword, [])
                if value not in temp_dict[entry.keyword]:
                    temp_dict[entry.keyword].append(value)

        with open(dest_path, 'w', encoding="utf-8") as of:
            for word in temp_dict.keys():
                for katakana, pitch_html in temp_dict[word]:
                    of.write(f"{word}\t{katakana}\t{pitch_html}\n")


if __name__ == '__main__':
    KanjiumDb.test()
