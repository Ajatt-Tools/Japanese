# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib

from japanese.helpers.file_ops import (
    find_config_json,
    rm_file,
    touch,
    user_files_dir,
    walk_parents,
)


def test_config_json() -> None:
    assert find_config_json().is_file()


def test_walk_parents() -> None:
    parents = [*walk_parents(__file__)]
    assert pathlib.Path(__file__).parent.samefile(parents[0])
    assert pathlib.Path("/").samefile(parents[-1])


def test_user_files_dir() -> None:
    assert user_files_dir().is_dir()


def test_file_touch_rm(tmp_path_factory) -> None:
    some_file = tmp_path_factory.mktemp("file_ops") / "file.txt"
    assert not some_file.is_file()
    touch(some_file)
    assert some_file.is_file()
    rm_file(some_file)
    assert not some_file.is_file()
