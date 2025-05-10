# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from collections.abc import Iterable, Sequence

RE_FLAGS = re.MULTILINE | re.IGNORECASE
HTML_AND_MEDIA_REGEX = re.compile(
    r"<[^<>]+>|\[sound:[^\[\]]+]",
    flags=RE_FLAGS,
)
RE_NON_JP = re.compile(
    # Reference: https://stackoverflow.com/questions/15033196/
    # Added arabic numbers.
    r"[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf０-９0-9]+",
    flags=RE_FLAGS,
)
RE_JP_SEP = re.compile(
    # Reference: https://wikiless.org/wiki/List_of_Japanese_typographic_symbols
    r"[\r\n\t仝　 ・、※【】「」〒◎×〃゜『』《》～〜~〽,.。"
    r"〄〇〈〉〓〔〕〖〗〘〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿！？…ヽヾゞ〱〲〳〵〴（）［］｛｝｟｠゠＝‥•◦﹅﹆＊♪♫♬♩ⓍⓁⓎ]+",
    flags=RE_FLAGS,
)
RE_COUNTERS = re.compile(
    # Extra: jp numbers 一二三四五六七八九十零
    r"([0-9０-９]+(?:万人|ヶ月|[つ月日人筋隻丁品番枚時回円万歳限]))",
    flags=RE_FLAGS,
)
RE_NON_JP_PARSED = re.compile(
    r"<no-jp>(?P<token>.*?)</no-jp>",
    flags=RE_FLAGS,
)
RE_NON_JP_PART = re.compile(
    r"(<no-jp>.*?</no-jp>)",
    flags=RE_FLAGS,
)
RE_ANKI_FURIGANA = re.compile(
    r" *([^ \[\]]+)\[[^\[\]]+]",
    flags=RE_FLAGS,
)


class Token(str):
    @property
    def word(self) -> str:
        return self

    headword = word

    @property
    def part_of_speech(self) -> None:
        return None


class ParseableToken(Token):
    pass


def split_separators(expr: str) -> list[str]:
    """Split text by common separators (like / or ・) into separate words that can be looked up."""

    # Replace all typical separators with a space
    expr = re.sub(RE_NON_JP, " ", expr)  # Remove non-Japanese characters
    expr = re.sub(RE_JP_SEP, " ", expr)  # Remove Japanese punctuation
    return expr.split(" ")


def clean_furigana(expr: str) -> str:
    """Remove text in [] used to represent furigana."""
    return re.sub(RE_ANKI_FURIGANA, r"\g<1>", expr)


def mark_non_jp_token(m: re.Match) -> str:
    return "<no-jp>" + m.group() + "</no-jp>"


def split_with_regex(expr: str, pattern: re.Pattern) -> list[str]:
    return re.split(
        RE_NON_JP_PART,
        string=re.sub(pattern, mark_non_jp_token, expr),
    )


def split_counters(text: str) -> Iterable[ParseableToken]:
    """Preemptively split text by words that mecab doesn't know how to parse."""
    for part in RE_COUNTERS.split(text):
        if part:
            yield ParseableToken(part)


SPLIT_REGEXES = (HTML_AND_MEDIA_REGEX, RE_NON_JP, RE_JP_SEP)


def split_with_next_regex(expr: str, regex_idx: int) -> Iterable[Token]:
    for part in split_with_regex(expr, SPLIT_REGEXES[regex_idx]):
        if part:
            if m := re.fullmatch(RE_NON_JP_PARSED, part):
                yield Token(m.group("token"))
            else:
                yield from _tokenize(part, regex_idx=regex_idx + 1)


def _tokenize(expr: str, *, regex_idx: int = 0) -> Iterable[Token]:
    if regex_idx < len(SPLIT_REGEXES):
        yield from split_with_next_regex(expr, regex_idx)
    else:
        yield from split_counters(expr.replace(" ", ""))


def tokenize(expr: str) -> Iterable[Token]:
    """
    Splits expr to tokens.
    Each token can be either parseable with mecab or not.
    Furigana is removed from parseable tokens, if present.
    """
    return _tokenize(expr=clean_furigana(expr))
