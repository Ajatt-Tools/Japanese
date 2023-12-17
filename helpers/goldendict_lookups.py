# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import subprocess
from distutils.spawn import find_executable

GD_PROGRAM_NAME = "GoldenDict-NG"
GD_EXE = find_executable("goldendict") or "/Applications/GoldenDict.app/Contents/MacOS/GoldenDict"


def lookup_goldendict(gd_word: str) -> subprocess.Popen:
    if GD_EXE is None:
        raise RuntimeError(f"{GD_PROGRAM_NAME} is not installed. Doing nothing.")
    return subprocess.Popen(
        (GD_EXE, gd_word),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    lookup_goldendict("肉じゃが")


if __name__ == '__main__':
    main()
