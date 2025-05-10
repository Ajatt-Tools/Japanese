# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
from typing import NamedTuple

from ..helpers.file_ops import user_files_dir


class DbFileSchema(NamedTuple):
    """
    Hold parameters of the database file.
    If the version changes in a future add-on release,
    the add-on opens a different sqlite3 file,
    thus avoiding errors that will otherwise occur due to mismatching tables, columns, etc.
    """

    prefix: str
    ver: str
    ext: str

    @property
    def name(self) -> str:
        return f"{self.prefix}.{self.ver}.{self.ext}"

    def remove_deprecated_files(self) -> None:
        for file in os.scandir(user_files_dir()):
            if file.name.startswith(self.prefix) and file.name.endswith(f".{self.ext}"):
                try:
                    schema = DbFileSchema(*file.name.split("."))
                except (ValueError, TypeError):
                    os.remove(file)
                    print(f"Removed invalid database file: {file.path}")
                else:
                    if schema.ver != self.ver:
                        os.remove(file)
                        print(f"Removed obsolete database file: {file.path}")


CURRENT_DB = DbFileSchema(
    prefix="audio_sources",
    ver="v2",
    ext="sqlite3",
)


def main():
    CURRENT_DB.remove_deprecated_files()


if __name__ == "__main__":
    main()
