# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import pickle

from aqt import mw
from aqt.operations import QueryOp

from .common import *
from .user_accents import UserAccentData


def read_formatted_accents() -> AccentDict:
    """ Read the formatted pitch accents file to memory. """
    acc_dict: AccentDict = collections.defaultdict(list)
    with open(FORMATTED_ACCENTS_TSV, encoding="utf-8") as f:
        for line in f:
            word, kana, *pitch_data = line.strip().split('\t')
            for key in (word, kana):
                entry = FormattedEntry(kana, *pitch_data)
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

    def reload_from_disk(self):
        """ Reads pitch accents file from disk. """
        print("Reading pitch accents file...")
        QueryOp(
            parent=mw,
            op=lambda collection: accents_dict_init(),
            success=lambda dictionary: self._reload_dict(dictionary),
        ).with_progress(
            "Reloading pitch accent dictionary..."
        ).run_in_background()

    def _reload_dict(self, new_dict: AccentDict):
        """ Reloads accent db (e.g. when the user changed settings). """
        print("Reloading accent dictionary...")
        self._db.clear()
        self._db = new_dict
        print(f"Total pitch accent entries: {len(self._db)}.")
