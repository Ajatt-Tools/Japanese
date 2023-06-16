# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pickle

from aqt import mw
from aqt.operations import QueryOp

from .common import *
from .kanjium_database import KanjiumDb
from .nhk_database import NhkDb
from .user_database import UserDb


def accents_dict_init() -> AccentDict:
    if not os.path.isdir(RES_DIR_PATH):
        raise OSError("Accent database folder is missing!")

    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if should_regenerate(FORMATTED_ACCENTS_PICKLE):
        print("The pickle needs updating.")
        derivative = generate_formatted_accents()
        with open(FORMATTED_ACCENTS_PICKLE, 'wb') as f:
            # Pickle the dictionary using the highest protocol available.
            pickle.dump(derivative, f, pickle.HIGHEST_PROTOCOL)
    else:
        print("Reading from existing accents pickle.")
        with open(FORMATTED_ACCENTS_PICKLE, 'rb') as f:
            derivative = pickle.load(f)

    # Finally, patch with user-defined entries.
    derivative.update(UserDb().create_derivative())
    return derivative


def generate_formatted_accents() -> AccentDict:
    nhk_db, kanjium_db = NhkDb(), KanjiumDb()
    freq_list = ReadingsFreq()
    # Read kanjium data, then extend existing entries with NHK data.
    # NHK data is more rich, it contains nasal and devoiced positions.
    derivative = kanjium_db.read_derivative()
    for keyword, entries in nhk_db.read_derivative().items():
        derivative.setdefault(keyword, []).extend(entries)
        # New data comes last and should overwrite existing data.
        unique = {(entry.katakana_reading, entry.pitch_number): entry for entry in derivative[keyword]}
        derivative[keyword] = sorted(
            unique.values(),
            key=lambda entry: freq_list[FreqLookUpKey(keyword, entry.katakana_reading)],
            reverse=True,
        )
    return derivative


class AccentDictManager:
    def __init__(self):
        self._db: AccentDict = AccentDict({})

    def __contains__(self, item: str):
        return self._db.__contains__(item)

    def __getitem__(self, item: str) -> Collection[FormattedEntry]:
        return self._db.__getitem__(item)

    def reload_from_disk(self):
        """ Reads accent database from disk. """
        print("Reading accent database...")
        QueryOp(
            parent=mw,
            op=lambda collection: accents_dict_init(),
            success=lambda dictionary: self._reload_dict(dictionary),
        ).with_progress(
            "Reloading pitch accent database..."
        ).run_in_background()

    def _reload_dict(self, new_dict: AccentDict):
        """ Reloads accent db (e.g. when the user changed settings). """
        print("Reloading accent database...")
        self._db.clear()
        self._db = new_dict
        print(f"Total pitch accent entries: {len(self._db)}.")
