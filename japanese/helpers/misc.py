# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import math
import re
from collections.abc import Iterable, Sequence
from typing import TypeVar

from anki.utils import html_to_text_line
from aqt import mw

from .tokens import RE_FLAGS

T = TypeVar("T")


def strip_html_and_media(text: str) -> str:
    assert mw
    return html_to_text_line(mw.col.media.strip(text)) if text else text


def split_list(input_list: Sequence[T], n_chunks: int) -> Iterable[Sequence[T]]:
    """Splits a list into N chunks."""
    chunk_size = math.ceil(len(input_list) / n_chunks)
    for i in range(0, len(input_list), chunk_size):
        yield input_list[i : i + chunk_size]


MEDIA_REGEX = re.compile(
    r"<img[^<>]+>|\[sound:[^\[\]]+]",
    flags=RE_FLAGS,
)


def media_strip(text: str) -> str:
    """Strip Anki media references from text, using a regex fallback outside Anki."""
    if not mw:
        # Anki isn't running.
        return MEDIA_REGEX.sub("", text)
    assert mw and mw.col, "Collection must be open."
    return mw.col.media.strip(text)


def compact_seq(seq: Iterable) -> Sequence:
    return tuple(dict.fromkeys(seq))
