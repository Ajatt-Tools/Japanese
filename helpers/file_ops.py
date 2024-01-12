# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import subprocess
from collections.abc import Iterable

from anki.utils import no_bundled_libs

THIS_ADDON_MODULE = __name__.split(".")[0]


def walk_parents(current_dir: str) -> Iterable[str]:
    while not os.path.samefile(parent_dir := os.path.dirname(current_dir), current_dir):
        yield parent_dir
        current_dir = parent_dir


def resolve_relative_path(*paths) -> str:
    """ Return path to file inside the add-on's dir. """
    for parent_dir in walk_parents(__file__):
        if os.path.basename(parent_dir) == THIS_ADDON_MODULE:
            return os.path.join(parent_dir, *paths)


def touch(path):
    with open(path, 'a'):
        os.utime(path, None)


def user_files_dir():
    """ Return path to the user files directory. """
    for parent_dir in walk_parents(__file__):
        if os.path.isdir(dir_path := os.path.join(parent_dir, "user_files")):
            return dir_path


def open_file(path: str) -> None:
    """
    Select file in lf, the preferred terminal file manager, or open it with xdg-open.
    """
    from aqt.qt import QDesktopServices, QUrl
    from distutils.spawn import find_executable

    if (terminal := os.getenv("TERMINAL")) and (lf := (os.getenv("FILE") or find_executable("lf"))):
        subprocess.Popen([terminal, "-e", lf, path, ], shell=False)
    elif opener := find_executable("xdg-open"):
        subprocess.Popen([opener, f"file://{path}", ], shell=False)
    else:
        with no_bundled_libs():
            QDesktopServices.openUrl(QUrl(f"file://{path}"))


if __name__ == '__main__':
    print(user_files_dir())
    print(open_file('/etc/hosts'))
