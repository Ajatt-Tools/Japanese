# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import NamedTuple, NewType, Sequence

try:
    from .consts import *
except ImportError:
    from consts import *


def is_old(file_path: str) -> bool:
    return any(
        os.path.getmtime(f.path) > os.path.getmtime(file_path)
        for f in os.scandir(THIS_DIR_PATH)
        if f.name.endswith('.py')
    )


def should_regenerate(file_path: str) -> bool:
    return (
            not os.path.isfile(file_path)
            or not os.path.getsize(file_path)
            or is_old(file_path)
    )


class FormattedEntry(NamedTuple):
    katakana_reading: str
    html_notation: str
    pitch_number: str

    def has_accent(self) -> bool:
        return self.pitch_number != NO_ACCENT

    @property
    def pitch_number_html(self):
        return f'<span class="pitch_number">{self.pitch_number}</span>'


AccentDict = NewType("AccentDict", dict[str, Sequence[FormattedEntry]])
