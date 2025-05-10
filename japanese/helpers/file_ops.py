# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import pathlib
import subprocess
from collections.abc import Iterable
from typing import Union

from anki.utils import no_bundled_libs

from ..ajt_common.utils import find_executable

THIS_ADDON_MODULE = __name__.split(".")[0]


def walk_parents(dir_or_file_path: Union[str, pathlib.Path]) -> Iterable[pathlib.Path]:
    current_dir = pathlib.Path(dir_or_file_path)
    if current_dir.is_dir():
        yield current_dir
    while not current_dir.samefile(parent_dir := current_dir.parent):
        yield parent_dir
        current_dir = parent_dir


def touch(path: Union[str, pathlib.Path]) -> None:
    with open(path, "a"):
        os.utime(path, None)


def rm_file(path: Union[str, pathlib.Path]) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def find_file_in_parents(file_name: str) -> pathlib.Path:
    """Used when testing/debugging."""
    for parent_dir in walk_parents(__file__):
        if (path := parent_dir.joinpath(file_name)).is_file():
            return path
    raise RuntimeError(f"couldn't find file '{file_name}'")


def find_config_json() -> pathlib.Path:
    """Used when testing/debugging."""
    return find_file_in_parents("config.json")


@functools.cache
def user_files_dir() -> pathlib.Path:
    """Return path to the user files directory."""
    for parent_dir in walk_parents(__file__):
        if (dir_path := parent_dir.joinpath("user_files")).is_dir():
            return dir_path
    raise RuntimeError("couldn't find user_files directory")


def open_file(path: str) -> None:
    """
    Select file in lf, the preferred terminal file manager, or open it with xdg-open.
    """
    from aqt.qt import QDesktopServices, QUrl

    if (terminal := os.getenv("TERMINAL")) and (lf := (os.getenv("FILE") or find_executable("lf"))):
        subprocess.Popen(
            [terminal, "-e", lf, path],
            shell=False,
            start_new_session=True,
        )
    elif opener := find_executable("xdg-open"):
        subprocess.Popen(
            [opener, f"file://{path}"],
            shell=False,
            start_new_session=True,
        )
    else:
        with no_bundled_libs():
            QDesktopServices.openUrl(QUrl(f"file://{path}"))


def file_exists(file_path: str) -> bool:
    return bool(file_path and os.path.isfile(file_path) and os.stat(file_path).st_size > 0)
