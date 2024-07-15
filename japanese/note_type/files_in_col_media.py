# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
import re
import typing
from collections.abc import Iterable

from aqt import mw

from .bundled_files import UNK_VERSION, FileVersionTuple, version_str_to_tuple

RE_AJT_CSS_IN_COL_FILENAME = re.compile(r"^_ajt_japanese_(?P<version>\d+\.\d+\.\d+\.\d+)\.css$")


class FileInCollection(typing.NamedTuple):
    name: str
    version: FileVersionTuple

    @classmethod
    def new(cls, file_name: str):
        m = re.fullmatch(RE_AJT_CSS_IN_COL_FILENAME, file_name)
        if m:
            return cls(file_name, version_str_to_tuple(m.group("version")))
        return cls(file_name, UNK_VERSION)


def find_ajt_script_names_in_collection() -> Iterable[pathlib.Path]:
    # Note: the official binary bundle is stuck on python 3.9; glob() does not support the root_dir parameter.
    assert mw
    return pathlib.Path(mw.col.media.dir()).glob("_ajt_japanese*.*")


def parse_ajt_script_names(file_names: Iterable[pathlib.Path]) -> frozenset[FileInCollection]:
    return frozenset(FileInCollection.new(file_name=path.name) for path in file_names)


def find_ajt_scripts_in_collection() -> frozenset[FileInCollection]:
    return parse_ajt_script_names(find_ajt_script_names_in_collection())
