# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import subprocess
from distutils.spawn import find_executable
from typing import Optional

from anki.utils import is_mac

GD_PROGRAM_NAME = "GoldenDict-NG"
GD_MACOS_PATH = "/Applications/GoldenDict.app/Contents/MacOS/GoldenDict"


def find_goldendict_fallback() -> Optional[str]:
    return is_mac and os.path.isfile(GD_MACOS_PATH) and GD_MACOS_PATH or None


@functools.cache
def find_goldendict() -> Optional[str]:
    return (
            find_executable("goldendict")
            or find_goldendict_fallback()
    )


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


def main():
    lookup_goldendict("肉じゃが")


if __name__ == '__main__':
    main()
