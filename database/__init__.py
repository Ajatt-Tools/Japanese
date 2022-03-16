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

import pickle

from .common import *
from .kanjium_database import KanjiumDb
from .nhk_database import NhkDb


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

    print(f"Total pitch accent entries: {len(derivative)}.")
    return derivative
