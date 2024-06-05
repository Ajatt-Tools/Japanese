# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

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


def test_word_reading() -> None:
    assert word_reading("テスト[1]") == WordReading(word="テスト", reading="1")
    assert word_reading("有[あ]り 得[う]る") == WordReading(word="有り得る", reading="ありうる")
    assert word_reading("有る") == WordReading(word="有る", reading="")
    assert word_reading("お 前[まい<br>まえ<br>めえ]") == WordReading(word="お前", reading="おまい<br>まえ<br>めえ")
    assert word_reading("もうお 金[かね]が 無[な]くなりました。") == WordReading(
        word="もうお金が無くなりました。", reading="もうおかねがなくなりました。"
    )
    assert word_reading(
        "妹[いもうと]は 自分[じぶん]の 我[わ]が 儘[まま]が 通[とお]らないと、すぐ 拗[す]ねる。"
    ) == WordReading(
        word="妹は自分の我が儘が通らないと、すぐ拗ねる。",
        reading="いもうとはじぶんのわがままがとおらないと、すぐすねる。",
    )


def test_mingle_readings() -> None:
    assert (
        mingle_readings([" 有[あ]り 得[う]る", " 有[あ]り 得[え]る", " 有[あ]り 得[え]る"]) == " 有[あ]り 得[う, え]る"
    )
    assert mingle_readings([" 故郷[こきょう]", " 故郷[ふるさと]"]) == " 故郷[こきょう, ふるさと]"
    assert mingle_readings(["お 前[まえ]", "お 前[めえ]"]) == "お 前[まえ, めえ]"
    assert mingle_readings([" 言[い]い 分[ぶん]", " 言い分[いーぶん]"]) == " 言[い]い 分[ぶん]"


def test_split_possible_furigana() -> None:
    assert split_possible_furigana("テスト[1]") == WordReading("テスト", "")
    assert split_possible_furigana("明後日[×あさって]") == WordReading("明後日", "")
    assert split_possible_furigana("明後日[あさって]") == WordReading("明後日", "あさって")
    assert split_possible_furigana("明後日[zzz]") == WordReading("明後日", "")
    assert split_possible_furigana("お 金[かね]") == WordReading("お金", "おかね")
