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

# Data source:
# https://raw.githubusercontent.com/mifunetoshiro/kanjium/master/data/source_files/raw/accents.txt

import pickle

from .common import *
from .kanjium_database import KanjiumDb
from .nhk_database import NhkDb


def ensure_derivatives() -> None:
    if not os.path.isdir(DB_DIR_PATH):
        raise IOError("Accent database folder is missing!")

    NhkDb.self_check()
    KanjiumDb.self_check()


def init() -> Dict[str, List[Tuple[str, str]]]:
    ensure_derivatives()

    # If the pickle exists and needs updating, remove it.
    if os.path.isfile(p := DERIVATIVE_PICKLE) and should_regenerate(p):
        os.remove(p)

    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if os.path.isfile(p := DERIVATIVE_PICKLE):
        with open(p, 'rb') as f:
            derivative = pickle.load(f)
    else:
        with open(p, 'wb') as f:
            # Read kanjium data, then overwrite existing entries with NHK data.
            # NHK data is more rich, it contains nasal and devoiced positions.
            derivative = KanjiumDb.read_derivative()
            derivative.update(NhkDb.read_derivative())
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(derivative, f, pickle.HIGHEST_PROTOCOL)

    print('Total pitch accent entries:', len(derivative.keys()))
    return derivative
