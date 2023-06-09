# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os

from .kanjium_database import KanjiumDb
from ..helpers.file_ops import touch, user_files_dir


class UserDb(KanjiumDb):
    _source_csv_path = os.path.join(user_files_dir(), "user_data.tsv")
    _formatted_csv_path = None

    def self_check(self):
        if not os.path.isfile(self._source_csv_path):
            touch(self._source_csv_path)
            print(f"Created file: {self._source_csv_path}")

    @classmethod
    def source_csv_path(cls) -> str:
        return cls._source_csv_path
