# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable, Sequence

import pytest

from japanese.helpers.tokens import Token, clean_furigana, tokenize


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "手紙[てがみ]は、 男[おとこ]らしく 潔[いさぎよ]い<b>筆致[ひっち]</b>で 書[か]かれていた。",
            "手紙は、男らしく潔い<b>筆致</b>で書かれていた。",
        ),
        (
            "富竹[とみたけ]さん 今[いま] 扉[とびら]の 南京錠[なんきんじょう]いじってませんでした？",
            "富竹さん今扉の南京錠いじってませんでした？",
        ),
    ],
)
def test_clean_furigana(text: str, expected: str) -> None:
    """Furigana brackets and their readings are removed, keeping the base text."""
    assert clean_furigana(text) == expected


def describe_result(tokens: Iterable[Token]) -> Sequence[str]:
    """Format tokens as ClassName(text) strings for comparison."""
    return tuple(f"{token.__class__.__name__}({token})" for token in tokens)


def test_tokenize() -> None:
    """Mixed HTML, media, and Japanese text split into the expected token sequence."""
    expr = (
        '<div>Lorem ipsum dolor sit amet, [sound:はな.mp3]<img src="はな.jpg"> '
        "consectetur adipiscing<br> elit <b>私達</b>は昨日ロンドンに着いた。おはよう。 Тест.</div>"
        "1月8日八日.彼女は１２月のある寒い夜に亡くなった。"
        " 情報処理[じょうほうしょり]の 技術[ぎじゅつ]は 日々[にちにち,ひび] 進化[しんか]している。"
    )
    expected = (
        "Token(<div>)",
        "Token(Lorem ipsum dolor sit amet, )",
        "Token([sound:はな.mp3])",
        'Token(<img src="はな.jpg">)',
        "Token( consectetur adipiscing)",
        "Token(<br>)",
        "Token( elit )",
        "Token(<b>)",
        "ParseableToken(私達)",
        "Token(</b>)",
        "ParseableToken(は昨日ロンドンに着いた)",
        "Token(。)",
        "ParseableToken(おはよう)",
        "Token(。)",
        "Token( Тест.)",
        "Token(</div>)",
        "ParseableToken(1月)",
        "ParseableToken(8日)",
        "ParseableToken(八日)",
        "Token(.)",
        "ParseableToken(彼女は)",
        "ParseableToken(１２月)",
        "ParseableToken(のある寒い夜に亡くなった)",
        "Token(。)",
        "ParseableToken(情報処理の技術は日々進化している)",
        "Token(。)",
    )
    assert describe_result(tokenize(expr)) == expected


def test_counter_tokenize() -> None:
    """A counter expression with a numeral splits into parseable tokens."""
    expr = "こうして３日間が始まった"
    expected = (
        "ParseableToken(こうして)",
        "ParseableToken(３日)",
        "ParseableToken(間が始まった)",
    )
    assert describe_result(tokenize(expr)) == expected


def test_empty_tokenize() -> None:
    """Empty input produces no tokens."""
    assert list(tokenize("")) == list()
