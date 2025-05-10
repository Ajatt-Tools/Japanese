# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import io
import re
from collections.abc import Iterable
from typing import Final, NamedTuple, Union

from .tokens import clean_furigana

MULTIPLE_READING_SEP: Final[str] = "・"


class SplitFurigana(NamedTuple):
    head: str
    reading: str
    suffix: str


class NoFurigana(str):
    @property
    def head(self):
        return self

    reading = head


class WordReading(NamedTuple):
    word: str
    reading: str


def strip_non_jp_furigana(expr: str) -> str:
    """Non-japanese furigana is not real furigana. Strip it."""
    return re.sub(r"\[[^ぁ-ゖァ-ヺｧ-ﾝ]+]", "", expr)


def find_head_reading_suffix(text: str) -> Union[SplitFurigana, NoFurigana]:
    """
    Locate where furigana starts and ends, return the three parts.
    Return text back if it doesn't contain furigana.
    """
    furigana_start, furigana_end = -1, -1
    for i, c in enumerate(text):
        if c == "[":
            furigana_start = i
        if c == "]":
            furigana_end = i
            break
    if 0 < furigana_start < furigana_end:
        return SplitFurigana(text[:furigana_start], text[furigana_start + 1 : furigana_end], text[furigana_end + 1 :])
    else:
        return NoFurigana(text)


def iter_split_parts(text: str) -> Iterable[Union[SplitFurigana, NoFurigana]]:
    while text and (part := find_head_reading_suffix(text)):
        yield part
        if isinstance(part, NoFurigana):
            break
        text = part.suffix


def decompose_word(text: str) -> SplitFurigana:
    """
    Takes furigana notation, splits it into (head, reading, suffix).
    "辛[から]い" == (head='辛', reading='から', suffix='い')
    "南[みなみ]千[ち]秋[あき]" == (head='南千秋', reading='みなみちあき', suffix='')
    """
    head, reading, suffix = io.StringIO(), io.StringIO(), io.StringIO()
    for num, part in enumerate(iter_split_parts(text)):
        if isinstance(part, NoFurigana) and num > 0:
            suffix.write(part)
        else:
            head.write(part.head)
            reading.write(part.reading)
    return SplitFurigana(head.getvalue(), reading.getvalue(), suffix.getvalue())


def tie_inside_furigana(s: str) -> str:
    def fixup(m: re.Match):
        return m.group().replace(" ", MULTIPLE_READING_SEP)

    return re.sub(r"\[[^\[\]]+?]", fixup, s)


def whitespace_split(furigana_notation: str) -> list[str]:
    """
    Splits text by whitespace, except whitespace inside furigana.
    """
    return tie_inside_furigana(furigana_notation).split()


def word_reading(text: str) -> WordReading:
    """
    Takes furigana notation, splits it into (word, reading).
    """
    word, reading = [], []
    for split in map(decompose_word, whitespace_split(text)):
        word.append(split.head + split.suffix)
        reading.append(split.reading + split.suffix)
    word, reading = "".join(word), "".join(reading)
    return WordReading(word, reading) if (reading and word != reading) else WordReading(text, "")


def pairs(seq: list):
    yield from zip(seq, seq[1:])


def mingle_readings(words_furigana: list[str], *, sep: str = ", ") -> str:
    """
    Takes several furigana notations, packs them into one, with readings separated by sep.

    readings = ["辛[から]い", "辛[つら]い",]
    output = " 辛[から, つら]い"
    """
    assert len(words_furigana) > 1

    packs = []
    split = list(map(whitespace_split, words_furigana))

    if any(len(x) != len(y) for x, y in pairs(split)):
        # When notations are inconsistent, don't attempt further parsing.
        return words_furigana[0]

    for first, *rest in zip(*split):
        first = decompose_word(first)
        words_furigana = sep.join(dict.fromkeys(word.reading for word in (first, *map(decompose_word, rest))))
        packs.append(f" {first.head}[{words_furigana}]{first.suffix}" if words_furigana != first.head else first.head)
    return "".join(packs)


def should_ignore_incorrect_reading(expr_reading: str, cfg_reading_sep: str) -> bool:
    """
    Don't bother handling readings that contain multiple different words or readings that are numbers.
    Sometimes the reading starts with x or ×, like 明後日[×あさって].
    Used to indicate that one of the two possible readings is not the answer.
    https://tatsumoto-ren.github.io/blog/discussing-various-card-templates.html#distinguishing-readings
    """
    return (
        expr_reading.isnumeric()
        or cfg_reading_sep.strip() in expr_reading
        or MULTIPLE_READING_SEP in expr_reading
        or expr_reading.startswith("x")
        or expr_reading.startswith("×")
    )


def split_possible_furigana(expr: str, cfg_reading_sep: str = ", ") -> WordReading:
    # Sometimes furigana notation is being used by the users to distinguish otherwise duplicate notes.
    # E.g., テスト[1], テスト[2]
    expr = strip_non_jp_furigana(expr)

    # If the expression contains furigana, split it.
    expr, expr_reading = word_reading(expr)
    expr, expr_reading = clean_furigana(expr), clean_furigana(expr_reading)

    # If there are numbers or multiple readings present, ignore all of them.
    if expr_reading and should_ignore_incorrect_reading(expr_reading, cfg_reading_sep):
        expr_reading = ""

    return WordReading(expr, expr_reading)
