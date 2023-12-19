# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import os
import subprocess
from distutils.spawn import find_executable
from typing import Optional

from anki.utils import is_mac

GD_PROGRAM_NAME = "GoldenDict-NG"


@functools.cache
def find_goldendict() -> Optional[str]:
    gd_exe = find_executable("goldendict")
    gd_macos_location = "/Applications/GoldenDict.app/Contents/MacOS/GoldenDict"
    if gd_exe is None and is_mac and os.path.isfile(gd_macos_location):
        gd_exe = gd_macos_location
    return gd_exe


def lookup_goldendict(gd_word: str) -> subprocess.Popen:
    if find_goldendict() is None:
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
