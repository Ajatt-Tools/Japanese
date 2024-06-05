# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import re
from collections.abc import Iterable, MutableSequence, Sequence
from typing import NamedTuple, NewType

from .consts import NO_ACCENT, PITCH_DIR_PATH


def is_dunder(name: str) -> bool:
    """Returns whether name is a dunder name."""
    return name.startswith("__") and name.endswith("__")


def files_in_dir(dir_path: str) -> Iterable[str]:
    return (
        os.path.normpath(os.path.join(root, file))
        for root, dirs, files in os.walk(dir_path)
        if is_dunder(os.path.basename(root)) is False
        for file in files
    )


def is_old(pickle_file_path: str) -> bool:
    """
    Return True if the file pointed by file_path is older than the other files.
    """
    return any(
        os.path.getmtime(cmp_file_path) > os.path.getmtime(pickle_file_path)
        for cmp_file_path in files_in_dir(PITCH_DIR_PATH)
    )


def should_regenerate(pickle_file_path: str) -> bool:
    """
    Return True if the pickle file pointed by file_path needs to be regenerated.
    """
    return not os.path.isfile(pickle_file_path) or os.path.getsize(pickle_file_path) < 1 or is_old(pickle_file_path)


class FormattedEntry(NamedTuple):
    katakana_reading: str
    html_notation: str
    pitch_number: str

    def has_accent(self) -> bool:
        return self.pitch_number != NO_ACCENT

    @property
    def pitch_number_html(self):
        return f'<span class="pitch_number">{self.pitch_number}</span>'


AccentDict = NewType("AccentDict", dict[str, MutableSequence[FormattedEntry]])

RE_PITCH_NUM = re.compile(r"\d+|\?")


def split_pitch_numbers(s: str) -> list[str]:
    return re.findall(RE_PITCH_NUM, s)
