# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import pathlib
import subprocess
from collections.abc import Iterable
from typing import Optional, Union

from anki.utils import no_bundled_libs

from ..ajt_common.utils import find_executable

THIS_ADDON_MODULE = __name__.split(".")[0]


def walk_parents(dir_or_file_path: str | pathlib.Path) -> Iterable[pathlib.Path]:
    current_dir = pathlib.Path(dir_or_file_path)
    if current_dir.is_dir():
        yield current_dir
    while not current_dir.samefile(parent_dir := current_dir.parent):
        yield parent_dir
        current_dir = parent_dir


def touch(path: str | pathlib.Path) -> None:
    with open(path, "a"):
        os.utime(path, None)


def rm_file(path: str | pathlib.Path) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def find_file_in_parents(file_name: str, start_from: str = __file__) -> pathlib.Path:
    """Used when testing/debugging."""
    for parent_dir in walk_parents(start_from):
        if (path := parent_dir.joinpath(file_name)).is_file():
            return path
    raise RuntimeError(f"couldn't find file '{file_name}'")


def find_config_json() -> pathlib.Path:
    """Used when testing/debugging."""
    return find_file_in_parents("config.json")


def get_anki_japanese_user_dir() -> pathlib.Path | None:
    # https://github.com/Ajatt-Tools/Japanese/issues/28#issuecomment-3788159617
    if anki_jp_user_dir := os.getenv("ANKI_JAPANESE_DIR"):
        return pathlib.Path(anki_jp_user_dir)
    return None


@functools.cache
def user_files_dir() -> pathlib.Path:
    """Return path to the user files directory."""
    if (anki_jp_user_dir := get_anki_japanese_user_dir()) and anki_jp_user_dir.is_dir():
        return anki_jp_user_dir
    for parent_dir in walk_parents(__file__):
        if (dir_path := parent_dir.joinpath("user_files")).is_dir():
            return dir_path
    raise RuntimeError("couldn't find user_files directory")


def file_exists(file_path: str) -> bool:
    return bool(file_path and os.path.isfile(file_path) and os.stat(file_path).st_size > 0)
