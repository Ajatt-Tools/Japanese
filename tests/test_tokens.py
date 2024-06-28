# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.helpers.tokens import clean_furigana, tokenize


def test_clean_furigana() -> None:
    assert (
        clean_furigana("手紙[てがみ]は、 男[おとこ]らしく 潔[いさぎよ]い<b>筆致[ひっち]</b>で 書[か]かれていた。")
        == "手紙は、男らしく潔い<b>筆致</b>で書かれていた。"
    )
    assert (
        clean_furigana("富竹[とみたけ]さん 今[いま] 扉[とびら]の 南京錠[なんきんじょう]いじってませんでした？")
        == "富竹さん今扉の南京錠いじってませんでした？"
    )


def _describe_result(tokens):
    return list(f"{token.__class__.__name__}({token})" for token in tokens)


def test_tokenize() -> None:
    expr = (
        '<div>Lorem ipsum dolor sit amet, [sound:はな.mp3]<img src="はな.jpg"> '
        "consectetur adipiscing<br> elit <b>私達</b>は昨日ロンドンに着いた。おはよう。 Тест.</div>"
        "1月8日八日.彼女は１２月のある寒い夜に亡くなった。"
        " 情報処理[じょうほうしょり]の 技術[ぎじゅつ]は 日々[にちにち,ひび] 進化[しんか]している。"
    )
    expected = [
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
    ]
    assert _describe_result(tokenize(expr)) == expected


def test_counter_tokenize() -> None:
    expr = "こうして３日間が始まった"
    expected = [
        "ParseableToken(こうして)",
        "ParseableToken(３日)",
        "ParseableToken(間が始まった)",
    ]
    assert _describe_result(tokenize(expr)) == expected


def test_empty_tokenize() -> None:
    assert list(tokenize("")) == list()
