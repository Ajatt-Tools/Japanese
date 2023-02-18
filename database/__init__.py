# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pickle

from .common import *
from .kanjium_database import KanjiumDb
from .nhk_database import NhkDb
from .user_database import UserDb


def init() -> AccentDict:
    if not os.path.isdir(DB_DIR_PATH):
        raise OSError("Accent database folder is missing!")

    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if os.path.isfile(DERIVATIVE_PICKLE):
        try:
            if should_regenerate(DERIVATIVE_PICKLE):
                raise RuntimeError("The pickle needs updating.")
            with open(DERIVATIVE_PICKLE, 'rb') as f:
                derivative = pickle.load(f)
        except (ModuleNotFoundError, RuntimeError) as e:
            print(e)
            os.remove(DERIVATIVE_PICKLE)
            return init()
    else:
        nhk_db, kanjium_db = NhkDb(), KanjiumDb()
        # Read kanjium data, then overwrite existing entries with NHK data.
        # NHK data is more rich, it contains nasal and devoiced positions.
        derivative = kanjium_db.read_derivative()
        for keyword, entries in nhk_db.read_derivative().items():
            derivative.setdefault(keyword, []).extend(entries)
            unique = {(entry.katakana_reading, entry.pitch_number): entry for entry in derivative[keyword]}
            derivative[keyword] = list(unique.values())
        with open(DERIVATIVE_PICKLE, 'wb') as f:
            # Pickle the dictionary using the highest protocol available.
            pickle.dump(derivative, f, pickle.HIGHEST_PROTOCOL)

    # Finally, patch with user-defined entries.
    derivative.update(UserDb(self_check=False).create_derivative())
    print(f"Total pitch accent entries: {len(derivative)}.")
    return derivative

def reload(db: AccentDict):
    """ Reloads accent db (e.g. when the user changed settings) """
    db.clear()
    db.update(init())
