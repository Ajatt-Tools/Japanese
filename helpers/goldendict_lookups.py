# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import subprocess
from distutils.spawn import find_executable

GOLDENDICT_EXE = find_executable("goldendict")


def lookup_goldendict(gd_word: str) -> subprocess.Popen:
    if GOLDENDICT_EXE is None:
        raise RuntimeError("GoldenDict-NG is not installed. Doing nothing.")
    return subprocess.Popen(
        (GOLDENDICT_EXE, gd_word),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def main():
    lookup_goldendict("肉じゃが")


if __name__ == '__main__':
    main()
