# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import os
import re
from typing import Dict, List, NamedTuple, Optional, NewType, Collection

# Paths to the database files and this particular file
THIS_DIR_PATH = os.path.dirname(os.path.normpath(__file__))
DB_DIR_PATH = os.path.join(THIS_DIR_PATH, "accent_dict")
DERIVATIVE_PICKLE = os.path.join(DB_DIR_PATH, "pronunciations_combined.pickle")
NO_ACCENT = "?"


def should_regenerate(file_path: str) -> bool:
    empty = not os.path.getsize(file_path)
    old = any(
        os.path.getmtime(os.path.join(THIS_DIR_PATH, f)) > os.path.getmtime(file_path)
        for f in os.listdir(THIS_DIR_PATH) if f.endswith('.py')
    )
    return empty or old


def kana_to_moras(kana: str) -> list[str]:
    return re.findall(r'.[ァィゥェォャュョぁぃぅぇぉゃゅょ]?', kana)


class FormattedEntry(NamedTuple):
    katakana_reading: str
    html_notation: str
    pitch_number: str

    def has_accent(self) -> bool:
        return self.pitch_number != NO_ACCENT

    @property
    def pitch_number_html(self):
        return f'<span class="pitch_number">{self.pitch_number}</span>'


AccentDict = NewType("AccentDict", dict[str, Collection[FormattedEntry]])


class AccDbManager(abc.ABC):
    accent_database: str = None
    derivative_database: str = None

    def __init__(self, self_check: bool = True, dest_path: Optional[str] = None):
        self._dest_path = dest_path or self.derivative_database
        if self_check:
            self.self_check()

    @classmethod
    def test(cls):
        if not os.path.isfile(cls.derivative_database):
            print("The derivative hasn't been built.")

        import filecmp
        import tempfile

        test_database = os.path.join(tempfile.gettempdir(), os.path.basename(cls.derivative_database))
        cls(self_check=False, dest_path=test_database).build_derivative()
        print('\n'.join(f'・{database}' for database in (test_database, cls.derivative_database)))
        are_equal = filecmp.cmp(cls.derivative_database, test_database, shallow=False)
        print('Equal.' if are_equal else 'Not equal!')

    def self_check(self):
        # First check that the original database is present.
        if not os.path.isfile(self.accent_database):
            raise OSError("Could not locate the source database!")

        # Generate the derivative database if it does not exist yet or needs updating.
        if not os.path.isfile(db := self.derivative_database) or should_regenerate(db):
            print("Will be rebuilt: ", os.path.basename(db))
            self.build_derivative()

    def read_derivative(self) -> AccentDict:
        """ Read the derivative file to memory """
        acc_dict = {}
        with open(self.derivative_database, encoding="utf-8") as f:
            for line in f:
                word, kana, *pitch_data = line.strip().split('\t')
                for key in (word, kana):
                    acc_dict.setdefault(key, [])
                    entry = FormattedEntry(kana, *pitch_data)
                    if entry not in acc_dict[key]:
                        acc_dict[key].append(entry)
        return AccentDict(acc_dict)

    @abc.abstractmethod
    def create_derivative(self) -> AccentDict:
        """ Produce the derived database. """
        raise NotImplementedError()

    def build_derivative(self) -> None:
        """ Build the derived database from the original database and save it as *.csv """
        self.save_derivative(self.create_derivative())

    def save_derivative(self, derivative: AccentDict) -> None:
        """ Dump the derived database to a *.csv file. """
        with open(self._dest_path, 'w', encoding="utf-8") as of:
            for word, entries in derivative.items():
                for entry in entries:
                    print(word, *entry, sep='\t', file=of)
