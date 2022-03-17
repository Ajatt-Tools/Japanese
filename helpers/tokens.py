# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import itertools
import re
from typing import Optional, List, Iterable

RE_FLAGS = re.MULTILINE | re.IGNORECASE
HTML_AND_MEDIA_REGEX = re.compile(
    r'<[^<>]+>|\[sound:[^\[\]]+]',
    flags=RE_FLAGS
)
NON_JP_REGEX = re.compile(
    # Reference: https://stackoverflow.com/questions/15033196/
    # Added `[` and `]` at the end to keep furigana notation.
    # Furigana notation is going to be parsed separately.
    # Added arabic numbers.
    r'[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf０-９0-9\]\[]+',
    flags=RE_FLAGS
)
JP_SEP_REGEX = re.compile(
    # Reference: https://wikiless.org/wiki/List_of_Japanese_typographic_symbols
    r'[仝　 ・、※【】「」〒◎×〃゜『』《》〜~〽,.。〄〇〈〉〓〔〕〖〗〘〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿！？…ヽヾゞ〱〲〳〵〴（）［］｛｝｟｠゠＝‥•◦﹅﹆＊♪♫♬♩ⓍⓁⓎ]',
    flags=RE_FLAGS
)
HALF_MONTHS = ("11月", "12月", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月")
FULL_MONTHS = ("１１月", "１２月", "１月", "２月", "３月", "４月", "５月", "６月", "７月", "８月", "９月", "１０月")
KANJI_MONTHS = ("十一月", "十二月", "一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月")
PEOPLE = ("一人", "二人", "1人", "2人")
SPECIAL_WORDS_REGEX = re.compile(rf'({"|".join(itertools.chain(HALF_MONTHS, FULL_MONTHS, KANJI_MONTHS, PEOPLE))})')


class Token(str):
    pass


class ParseableToken(Token):
    pass


def split_separators(expr: str) -> List[str]:
    """ Split text by common separators (like / or ・) into separate words that can be looked up. """

    # Replace all typical separators with a space
    expr = re.sub(NON_JP_REGEX, ' ', expr)  # Remove non-Japanese characters
    expr = re.sub(JP_SEP_REGEX, ' ', expr)  # Remove Japanese punctuation
    return expr.split(' ')


def clean_furigana(expr: str) -> str:
    return re.sub(r'([^ \[\]]+)\[[^ \[\]]+]', r'\g<1>', expr, flags=RE_FLAGS).replace(' ', '')


def split_special_words(text: str) -> Iterable[ParseableToken]:
    """ Preemptively split text by words that mecab doesn't know how to parse. """
    for part in re.split(SPECIAL_WORDS_REGEX, text):
        if part:
            yield ParseableToken(part)


def mark_non_jp_token(m: re.Match) -> str:
    return "<no-jp>" + m.group() + "</no-jp>"


def tokenize(expr: str, regexes: Optional[List[re.Pattern]] = None) -> Iterable[Token]:
    """
    Splits expr to tokens.
    Each token can be either parseable with mecab or not.
    Furigana is removed from parseable tokens, if present.
    """
    regexes = regexes or [HTML_AND_MEDIA_REGEX, NON_JP_REGEX, JP_SEP_REGEX]
    expr = re.sub(regexes[0], mark_non_jp_token, expr)

    for part in re.split(r'(<no-jp>.*?</no-jp>)', expr, flags=RE_FLAGS):
        if part:
            if m := re.fullmatch(r'<no-jp>(.*?)</no-jp>', part, flags=RE_FLAGS):
                yield Token(m.group(1))
            elif len(regexes) > 1:
                yield from tokenize(part, regexes[1:])
            else:
                yield from split_special_words(clean_furigana(part))


def main():
    print(clean_furigana("富竹[とみたけ]さん 今[いま] 扉[とびら]の 南京錠[なんきんじょう]いじってませんでした？"))

    expr = (
        "<div>Lorem ipsum dolor sit amet, [sound:はな.mp3]<img src=\"はな.jpg\"> "
        "consectetur adipiscing<br> elit <b>私達</b>は昨日ロンドンに着いた。おはよう。 Тест.</div>"
        "1月.彼女は１２月のある寒い夜に亡くなった。"
        "振り仮名[ふりがな]"
    )
    for token in tokenize(expr):
        print(f"{token.__class__.__name__}({token})")


if __name__ == '__main__':
    main()