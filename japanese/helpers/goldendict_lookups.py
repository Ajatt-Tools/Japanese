# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import subprocess
from typing import Optional

from anki.utils import is_mac

from ..ajt_common.utils import find_executable

GD_PROGRAM_NAME = "GoldenDict-NG"
GD_MACOS_PATH = (
    "/Applications/GoldenDict-ng.app/Contents/MacOS/GoldenDict-ng",
    "/Applications/GoldenDict.app/Contents/MacOS/GoldenDict",
)


def find_goldendict_fallback() -> Optional[str]:
    if not is_mac:
        return None
    for path in GD_MACOS_PATH:
        if os.path.isfile(path):
            return path
    return None


@functools.cache
def find_goldendict() -> Optional[str]:
    return find_executable("goldendict") or find_goldendict_fallback()


def lookup_goldendict(gd_word: str) -> subprocess.Popen:
    if not find_goldendict():
        raise RuntimeError(f"{GD_PROGRAM_NAME} is not installed. Doing nothing.")
    return subprocess.Popen(
        (find_goldendict(), gd_word),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
