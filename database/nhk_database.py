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
from typing import NamedTuple

try:
    from .common import *
except ImportError:
    from common import *


class AccentEntry(NamedTuple):
    NID: str
    ID: str
    WAVname: str
    K_FLD: str
    ACT: str
    katakana_reading: str
    nhk: str
    kanjiexpr: str
    NHKexpr: str
    numberchars: str
    devoiced_pos: str
    nasalsoundpos: str
    majiri: str
    kaisi: str
    KWAV: str
    katakana_reading_alt: str
    akusentosuu: str
    bunshou: str
    accent: str


def make_accent_entry(csv_line: str) -> AccentEntry:
    csv_line = csv_line.strip()
    # Special entries in the CSV file that have to be escaped
    # to prevent them from being treated as multiple fields.
    sub_entries = re.findall(r'({.*?,.*?})', csv_line) + re.findall(r'(\(.*?,.*?\))', csv_line)
    for s in sub_entries:
        csv_line = csv_line.replace(s, s.replace(',', ';'))

    return AccentEntry(*csv_line.split(','))


def format_nasal_or_devoiced_positions(expr: str):
    # Sometimes the expr ends with 10
    if expr.endswith('10'):
        expr = expr[:-2]
        result = [10]
    else:
        result = []

    return result + [int(pos) for pos in expr.split('0') if pos]


def format_entry(e: AccentEntry) -> str:
    """ Format an entry from the data in the original database to something that uses html """
    kana_reading, acc_pattern = e.katakana_reading_alt, e.accent

    # Fix accent notation by prepending zeros for moraes where accent info is omitted in the CSV.
    acc_pattern = "0" * (len(kana_reading) - len(acc_pattern)) + acc_pattern

    # Get the nasal positions
    nasal = format_nasal_or_devoiced_positions(e.nasalsoundpos)

    # Get the devoiced positions
    devoiced = format_nasal_or_devoiced_positions(e.devoiced_pos)

    result_str = []
    overline_flag = False

    for idx, acc in enumerate(int(pos) for pos in acc_pattern):
        # Start or end overline when necessary
        if not overline_flag and acc > 0:
            result_str.append('<span class="overline">')
            overline_flag = True
        if overline_flag and acc == 0:
            result_str.append('</span>')
            overline_flag = False

        # Wrap character if it's devoiced, else add as is.
        if (idx + 1) in devoiced:
            result_str.append(f'<span class="nopron">{kana_reading[idx]}</span>')
        else:
            result_str.append(kana_reading[idx])

        if (idx + 1) in nasal:
            result_str.append('<span class="nasal">&#176;</span>')

        # If we go down in pitch, add the downfall
        if acc == 2:
            result_str.append('</span>&#42780;')
            overline_flag = False

    # Close the overline if it's still open
    if overline_flag:
        result_str.append('</span>')

    return ''.join(result_str)


class NhkDb(AccDbManager):
    accent_database = os.path.join(DB_DIR_PATH, "nhk_data.csv")
    derivative_database = os.path.join(DB_DIR_PATH, "nhk_pronunciation.csv")

    def build_derivative(self) -> None:
        """ Build the derived database from the original database and save it as *.csv """
        with open(self.accent_database, encoding="utf-8") as f:
            entries: List[AccentEntry] = [make_accent_entry(line) for line in f]

        for entry in entries:
            value = FormattedEntry(entry.katakana_reading, format_entry(entry), None)

            # Add expressions for both
            for key in (entry.nhk, entry.kanjiexpr):
                self._temp_dict.setdefault(key, [])
                if value not in self._temp_dict[key]:
                    self._temp_dict[key].append(value)

        self.save_derivative()


if __name__ == '__main__':
    NhkDb.test()
