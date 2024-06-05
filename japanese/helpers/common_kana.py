# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    from ..mecab_controller.kana_conv import is_kana_str
    from ..mecab_controller.kana_conv import to_katakana as _
except ImportError:
    from mecab_controller.kana_conv import is_kana_str
    from mecab_controller.kana_conv import to_katakana as _


def adjust_to_inflection(raw_word: str, headword: str, headword_reading: str) -> str:
    """
    Adjusts the word's reading to match its conjugated form.
    E.g., if raw_word is 食べた and the reading is たべる, it should output たべた.
    """
    if _(headword) == _(headword_reading):
        return raw_word
    if _(headword) == _(raw_word):
        return headword_reading
    if is_kana_str(raw_word):
        return raw_word

    # Analyze the headword.
    # Go from the last to the first character
    # and skip the characters that are identical between the headword and the reading.
    # In the end, the reading of a common `stem` should be found, e.g. "ひざまず" for "跪かなかった"
    idx_headword, idx_reading = len(headword), len(headword_reading)
    while _(headword[idx_headword - 1]) == _(headword_reading[idx_reading - 1]):
        idx_headword -= 1
        idx_reading -= 1
    stem_reading = headword_reading[:idx_reading]
    inflected_reading = raw_word[idx_headword:]

    if _(stem_reading) == _(headword_reading):
        return headword_reading
    return stem_reading + inflected_reading


# Debug
##########################################################################


def main():
    assert adjust_to_inflection("食べた", "食べる", "たべる") == "たべた"
    assert adjust_to_inflection("跪いた", "跪く", "ひざまずく") == "ひざまずいた"
    assert adjust_to_inflection("跪かなかった", "跪く", "ひざまずく") == "ひざまずかなかった"
    assert adjust_to_inflection("安くなかった", "安い", "やすい") == "やすくなかった"
    assert adjust_to_inflection("繋りたい", "繋る", "つながる") == "つながりたい"
    assert adjust_to_inflection("言い方", "言い方", "いいかた") == "いいかた"
    assert adjust_to_inflection("やり遂げさせられない", "やり遂げる", "やりとげる") == "やりとげさせられない"
    assert adjust_to_inflection("死ん", "死ぬ", "しぬ") == "しん"
    assert adjust_to_inflection("たべた", "たべる", "たべる") == "たべた"
    assert adjust_to_inflection("カタカナ", "カタカナ", "かたかな") == "カタカナ"
    assert adjust_to_inflection("相合い傘", "相合い傘", "あいあいがさ") == "あいあいがさ"
    assert adjust_to_inflection("いた目", "板目", "いため") == "いため"
    assert adjust_to_inflection("軽そう", "軽装", "けいそー") == "けいそー"
    assert adjust_to_inflection("唸りました", "唸る", "うなる") == "うなりました"
    assert adjust_to_inflection("可愛くない", "可愛い", "かわいい") == "かわいくない"
    assert adjust_to_inflection("かわいくない", "可愛い", "かわいい") == "かわいくない"

    print("Passed.")


if __name__ == "__main__":
    main()
