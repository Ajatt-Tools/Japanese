# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

from .kanjium_database import KanjiumDb
from ..helpers.file_ops import touch, user_files_dir


class UserDb(KanjiumDb):
    accent_database = os.path.join(user_files_dir(), "user_data.tsv")
    derivative_database = None

    def self_check(self):
        if not os.path.isfile(self.accent_database):
            touch(self.accent_database)
            print(f"Created file: {self.accent_database}")
