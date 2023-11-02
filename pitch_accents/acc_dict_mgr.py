# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import csv
import pickle
from typing import Optional

from aqt import mw
from aqt.operations import QueryOp

try:
    from .common import *
    from .user_accents import UserAccentData
    from ..mecab_controller.kana_conv import to_katakana, to_hiragana
except ImportError:
    from common import *
    from user_accents import UserAccentData
    from mecab_controller.kana_conv import to_katakana, to_hiragana


def read_formatted_accents() -> AccentDict:
    """
    Read the formatted pitch accents file to memory.
    Place items in a list to retain the provided order of readings.

    Example entry as it appears in the formatted file:
    新年会 シンネンカイ <low_rise>シ</low_rise><high_drop>ンネ</high_drop><low>ンカイ</low> 3
    """
    acc_dict: AccentDict = collections.defaultdict(list)
    with open(FORMATTED_ACCENTS_TSV, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        for word, kana, *pitch_data in reader:
            entry = FormattedEntry(kana, *pitch_data)
            for key in (word, kana):
                if entry not in acc_dict[key]:
                    acc_dict[key].append(entry)
    acc_dict = AccentDict({
        headword: tuple(entries)
        for headword, entries in acc_dict.items()
    })
    return acc_dict


def accents_dict_init() -> AccentDict:
    if not os.path.isdir(RES_DIR_PATH):
        raise OSError("Pitch accents folder is missing!")

    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if should_regenerate(FORMATTED_ACCENTS_PICKLE):
        print("The pickle needs updating.")
        acc_dict = read_formatted_accents()
        with open(FORMATTED_ACCENTS_PICKLE, 'wb') as f:
            # Pickle the dictionary using the highest protocol available.
            pickle.dump(acc_dict, f, pickle.HIGHEST_PROTOCOL)
    else:
        print("Reading from existing accents pickle.")
        with open(FORMATTED_ACCENTS_PICKLE, 'rb') as f:
            acc_dict = pickle.load(f)

    # Finally, patch with user-defined entries.
    acc_dict.update(UserAccentData().create_formatted())
    return acc_dict


class AccentDictManager:
    def __init__(self):
        self._db: AccentDict = AccentDict({})

    def __contains__(self, item: str):
        return self._db.__contains__(item)

    def __getitem__(self, item: str) -> Sequence[FormattedEntry]:
        return self._db.__getitem__(item)

    def lookup(self, expr: str) -> Optional[Sequence[FormattedEntry]]:
        """
        Look up various forms of expr in accent db.
        Return None if there's no pitch accent for expr.
        """
        for variant in (expr, to_katakana(expr), to_hiragana(expr)):
            if variant in self:
                return self[variant]

    def reload_from_disk(self):
        """ Reads pitch accents file from disk. """
        print("Reading pitch accents file...")
        QueryOp(
            parent=mw,
            op=lambda collection: accents_dict_init(),
            success=lambda dictionary: self._reload_dict(dictionary),
        ).without_collection(
        ).with_progress(
            "Reloading pitch accent dictionary..."
        ).run_in_background()

    def _reload_dict(self, new_dict: AccentDict):
        """ Reloads accent db (e.g. when the user changed settings). """
        print("Reloading accent dictionary...")
        self._db.clear()
        self._db = new_dict
        print(f"Total pitch accent entries: {len(self._db)}.")


def main():
    acc_dict = accents_dict_init()
    for word, entries in acc_dict.items():
        for entry in entries:
            print(f"{word}\t{entry.katakana_reading}\t{entry.pitch_number}")


if __name__ == '__main__':
    main()
