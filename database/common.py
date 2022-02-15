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

import abc
import os
from typing import Dict, List, NamedTuple

# Paths to the database files and this particular file
THIS_DIR_PATH = os.path.dirname(os.path.normpath(__file__))
DB_DIR_PATH = os.path.join(THIS_DIR_PATH, "accent_dict")
DERIVATIVE_PICKLE = os.path.join(DB_DIR_PATH, "pronunciations_combined.pickle")


def should_regenerate(file_path: str) -> bool:
    return any(
        os.path.getmtime(os.path.join(THIS_DIR_PATH, f)) > os.path.getmtime(file_path)
        for f in os.listdir(THIS_DIR_PATH) if f.endswith('.py')
    )


class FormattedEntry(NamedTuple):
    katakana_reading: str
    html_notation: str


class AccDbManager(abc.ABC):
    accent_database: str = None
    derivative_database: str = None

    def __init__(self):
        self.self_check()

    @classmethod
    def test(cls):
        if not os.path.isfile(cls.derivative_database):
            print("The derivative hasn't been built.")

        import filecmp
        test_database = os.path.join(DB_DIR_PATH, "test.csv")
        cls().build_derivative(dest_path=test_database)
        print('Equal.' if filecmp.cmp(cls.derivative_database, test_database, shallow=False) else 'Not equal!')

    @abc.abstractmethod
    def build_derivative(self, dest_path: str = None):
        raise NotImplementedError()

    def self_check(self):
        # First check that the original database is present.
        if not os.path.isfile(self.accent_database):
            raise OSError("Could not locate the source database!")

        # Generate the derivative database if it does not exist yet or needs updating.
        if not os.path.isfile(db := self.derivative_database) or should_regenerate(db):
            print("Will be rebuilt: ", os.path.basename(db))
            self.build_derivative()

    def read_derivative(self) -> Dict[str, List[FormattedEntry]]:
        """ Read the derivative file to memory """
        acc_dict = {}
        with open(self.derivative_database, encoding="utf-8") as f:
            for line in f:
                word, kana, pitch_html = line.strip().split('\t')
                for key in (word, kana):
                    acc_dict.setdefault(key, [])
                    entry = FormattedEntry(kana, pitch_html)
                    if entry not in acc_dict[key]:
                        acc_dict[key].append(entry)

        return acc_dict

    @staticmethod
    def save_derivative(temp_dict: Dict[str, List[FormattedEntry]], dest_path: str) -> None:
        with open(dest_path, 'w', encoding="utf-8") as of:
            for word, entries in temp_dict.items():
                for entry in entries:
                    of.write(f"{word}\t{entry.katakana_reading}\t{entry.html_notation}\n")
