# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib

DATA_DIR = pathlib.Path(__file__).parent / "data"

try:
    # https://github.com/beartype/beartype
    from beartype.claw import beartype_this_package

    beartype_this_package()
except ImportError:
    pass
