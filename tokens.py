# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from typing import Optional, List, NamedTuple, Iterable

HTML_AND_MEDIA_REGEX = re.compile(
    r'<[^<>]+>|\[sound:[^\[\]]+]',
    re.U
)
NON_JP_REGEX = re.compile(
    # Reference: https://stackoverflow.com/questions/15033196/
    r'[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf]+',
    re.U
)
JP_SEP_REGEX = re.compile(
    r'[ ・、※【】「」〒◎×〃゜『』《》〜〽。〄〇〈〉〓〔〕〖〗〘〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿！？…]',
    re.U
)


class Token(NamedTuple):
    text: str
    mecab_parsable: bool = False


def mark_non_jp_token(m: re.Match) -> str:
    return "<no-jp>" + m.group() + "</no-jp>"


def tokenize(expr: str, regexes: Optional[List[re.Pattern]] = None) -> Iterable[Token]:
    regexes = regexes or [HTML_AND_MEDIA_REGEX, NON_JP_REGEX, JP_SEP_REGEX]
    expr = re.sub(regexes[0], mark_non_jp_token, expr)

    for token in re.split(r'(<no-jp>.*?</no-jp>)', expr):
        if token:
            if m := re.fullmatch(r'<no-jp>(.*?)</no-jp>', token):
                yield Token(m.group(1))
            elif len(regexes) > 1:
                yield from tokenize(token, regexes[1:])
            else:
                yield Token(token, mecab_parsable=True)


def main():
    expr = (
        "<div>Lorem ipsum dolor sit amet, [sound:はな.mp3]<img src=\"はな.jpg\"> "
        "consectetur adipiscing<br> elit <b>私達</b>は昨日ロンドンに着いた。おはよう。 Тест.</div>"
    )
    for token in tokenize(expr):
        print(token)


if __name__ == '__main__':
    main()
