# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os
from typing import Iterable

from .kanjium_database import KanjiumDb


def walk_parents(current_dir: str) -> Iterable[str]:
    while not os.path.samefile(parent_dir := os.path.dirname(current_dir), current_dir):
        yield parent_dir
        current_dir = parent_dir


def addon_module():
    return __name__.split('.')[0]


def resolve_relative_path(*paths) -> str:
    """ Return path to file inside the add-on's dir. """
    for parent_dir in walk_parents(os.path.abspath(__file__)):
        if os.path.basename(parent_dir) == addon_module():
            return os.path.join(parent_dir, *paths)


def touch(path):
    with open(path, 'a'):
        os.utime(path, None)


class UserDb(KanjiumDb):
    accent_database = resolve_relative_path("user_files", "user_data.tsv")
    derivative_database = None

    def self_check(self):
        if not os.path.isfile(self.accent_database):
            touch(self.accent_database)
            print(f"Created file: {self.accent_database}")
