# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from .kanjium_database import KanjiumDb
from ..helpers import resolve_file


class UserDb(KanjiumDb):
    accent_database = resolve_file("user_files", "user_data.tsv")
    derivative_database = None
