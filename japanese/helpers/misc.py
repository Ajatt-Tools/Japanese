# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import math
from collections.abc import Iterable, Sequence
from typing import Callable, TypeVar, Union

from anki.utils import html_to_text_line
from aqt import mw
from aqt.qt import pyqtBoundSignal, pyqtSignal

T = TypeVar("T")


def strip_html_and_media(text: str) -> str:
    assert mw
    return html_to_text_line(mw.col.media.strip(text)) if text else text


def split_list(input_list: Sequence[T], n_chunks: int) -> Iterable[Sequence[T]]:
    """Splits a list into N chunks."""
    chunk_size = math.ceil(len(input_list) / n_chunks)
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i : i + chunk_size]
