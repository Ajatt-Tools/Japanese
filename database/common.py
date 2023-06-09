# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import re
from typing import NamedTuple, Optional, NewType, Collection

try:
    from .consts import *
except ImportError:
    from consts import *


def should_regenerate(file_path: str) -> bool:
    empty = not os.path.getsize(file_path)
    old = any(
        os.path.getmtime(os.path.join(THIS_DIR_PATH, f)) > os.path.getmtime(file_path)
        for f in os.listdir(THIS_DIR_PATH) if f.endswith('.py')
    )
    return empty or old


def kana_to_moras(kana: str) -> list[str]:
    return re.findall(r'.゚?[ァィゥェォャュョぁぃぅぇぉゃゅょ]?', kana)


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
    _source_csv_path: str = None
    _formatted_csv_path: str = None

    def __init__(self, self_check: bool = True, dest_path: Optional[str] = None):
        self._dest_path = dest_path or self._formatted_csv_path
        if self_check:
            self.self_check()

    @classmethod
    def test(cls):
        if not os.path.isfile(cls._formatted_csv_path):
            print("The derivative hasn't been built.")

        import filecmp
        import tempfile

        test_database = os.path.join(tempfile.gettempdir(), os.path.basename(cls._formatted_csv_path))
        cls(self_check=False, dest_path=test_database).build_derivative()
        print('\n'.join(f'・{database}' for database in (test_database, cls._formatted_csv_path)))
        are_equal = filecmp.cmp(cls._formatted_csv_path, test_database, shallow=False)
        print('Equal.' if are_equal else 'Not equal!')

    def self_check(self):
        # First check that the original database is present.
        if not os.path.isfile(self._source_csv_path):
            raise OSError("Could not locate the source csv file!")

        # Generate the derivative database if it does not exist yet or needs updating.
        if not os.path.isfile(db := self._formatted_csv_path) or should_regenerate(db):
            print("Will be rebuilt: ", os.path.basename(db))
            self.build_derivative()

    def read_derivative(self) -> AccentDict:
        """ Read the derivative file to memory. """
        acc_dict = {}
        with open(self._formatted_csv_path, encoding="utf-8") as f:
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
        """ Build the derived csv from the original csv and save it as *.csv """
        self.save_derivative(self.create_derivative())

    def save_derivative(self, derivative: AccentDict) -> None:
        """ Dump the derived csv to a *.csv file. """
        with open(self._dest_path, 'w', encoding="utf-8") as of:
            for word, entries in derivative.items():
                for entry in entries:
                    print(word, *entry, sep='\t', file=of)
