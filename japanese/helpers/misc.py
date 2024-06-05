# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import math
from collections.abc import Iterable, Sequence
from typing import Callable, TypeVar, Union

from anki.utils import html_to_text_line
from aqt import mw
from aqt.qt import pyqtBoundSignal, pyqtSignal

T = TypeVar("T")


def strip_html_and_media(text: str) -> str:
    return html_to_text_line(mw.col.media.strip(text)) if text else text


def clamp(min_val: int, val: int, max_val: int) -> int:
    return max(min_val, min(val, max_val))


def split_list(input_list: Sequence[T], n_chunks: int) -> Iterable[Sequence[T]]:
    """Splits a list into N chunks."""
    chunk_size = math.ceil(len(input_list) / n_chunks)
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i : i + chunk_size]


def q_emit(signal: Union[Callable, pyqtSignal, pyqtBoundSignal]) -> None:
    """Helper to work around type checking not working with signal.emit(func)."""
    signal.emit()  # type: ignore
