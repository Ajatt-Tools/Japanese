# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.mingle_readings import (
    SplitFurigana,
    WordReading,
    decompose_word,
    mingle_readings,
    split_possible_furigana,
    strip_non_jp_furigana,
    whitespace_split,
    word_reading,
)


def test_decompose_word() -> None:
    assert decompose_word("故郷[こきょう]") == SplitFurigana(head="故郷", reading="こきょう", suffix="")
    assert decompose_word("有[あ]り") == SplitFurigana(head="有", reading="あ", suffix="り")
    assert decompose_word("ひらがな") == SplitFurigana(head="ひらがな", reading="ひらがな", suffix="")
    assert decompose_word("南[みなみ]千[ち]秋[あき]") == SplitFurigana(head="南千秋", reading="みなみちあき", suffix="")


def test_whitespace_split() -> None:
    assert whitespace_split(" 有[あ]り 得[う]る") == ["有[あ]り", "得[う]る"]


def test_strip_non_jp_furigana() -> None:
    assert strip_non_jp_furigana("悪[わる][1223]い[2]") == "悪[わる]い"


@pytest.mark.parametrize(
    "furigana, expected",
    [
        ("テスト[1]", WordReading("テスト", "1")),
        ("有[あ]り 得[う]る", WordReading("有り得る", "ありうる")),
        ("有る", WordReading("有る", "")),
        ("お 前[まい<br>まえ<br>めえ]", WordReading("お前", "おまい<br>まえ<br>めえ")),
        (
            "もうお 金[かね]が 無[な]くなりました。",
            WordReading("もうお金が無くなりました。", "もうおかねがなくなりました。"),
        ),
        (
            "妹[いもうと]は 自分[じぶん]の 我[わ]が 儘[まま]が 通[とお]らないと、すぐ 拗[す]ねる。",
            WordReading(
                "妹は自分の我が儘が通らないと、すぐ拗ねる。", "いもうとはじぶんのわがままがとおらないと、すぐすねる。"
            ),
        ),
    ],
)
def test_word_reading(furigana: str, expected: WordReading) -> None:
    assert word_reading(furigana) == expected


@pytest.mark.parametrize(
    "readings, expected",
    [
        ([" 有[あ]り 得[う]る", " 有[あ]り 得[え]る", " 有[あ]り 得[え]る"], " 有[あ]り 得[う, え]る"),
        ([" 故郷[こきょう]", " 故郷[ふるさと]"], " 故郷[こきょう, ふるさと]"),
        (["お 前[まえ]", "お 前[めえ]"], "お 前[まえ, めえ]"),
        ([" 言[い]い 分[ぶん]", " 言い分[いーぶん]"], " 言[い]い 分[ぶん]"),
        (["ほほ 笑[え]む", "ほほ 笑[え]む"], "ほほ 笑[え]む"),
    ],
)
def test_mingle_readings(readings: list[str], expected: str) -> None:
    assert mingle_readings(readings) == expected


@pytest.mark.parametrize(
    "furigana, expected",
    [
        ("テスト[1]", WordReading("テスト", "")),
        ("明後日[×あさって]", WordReading("明後日", "")),
        ("明後日[あさって]", WordReading("明後日", "あさって")),
        ("明後日[zzz]", WordReading("明後日", "")),
        ("お 金[かね]", WordReading("お金", "おかね")),
        ("日", WordReading("日", "")),
    ],
)
def test_split_possible_furigana(furigana: str, expected: WordReading) -> None:
    assert split_possible_furigana(furigana) == expected
