# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    from ..mecab_controller.kana_conv import to_katakana as _
except ImportError:
    from mecab_controller.kana_conv import to_katakana as _


def adjust_reading(raw_word: str, headword: str, headword_reading: str):
    """
    Adjusts the word's reading to match its conjugated form.
    E.g., if raw_word is 食べた, should output たべた.
    """
    if _(headword) == _(headword_reading):
        return raw_word
    if _(headword) == _(raw_word):
        return headword_reading
    idx_headword, idx_reading = len(headword), len(headword_reading)
    while _(headword[idx_headword - 1]) == _(headword_reading[idx_reading - 1]):
        idx_headword -= 1
        idx_reading -= 1
    return headword_reading[:idx_reading] + raw_word[idx_headword:]


def main():
    assert (adjust_reading('跪いた', '跪く', 'ひざまずく')) == 'ひざまずいた'
    assert (adjust_reading('安くなかった', '安い', 'やすい')) == 'やすくなかった'
    assert (adjust_reading('繋りたい', '繋る', 'つながる')) == 'つながりたい'
    assert (adjust_reading('言い方', '言い方', 'いいかた')) == 'いいかた'
    assert (adjust_reading('やり遂げさせられない', 'やり遂げる', 'やりとげる')) == 'やりとげさせられない'
    assert (adjust_reading('死ん', '死ぬ', 'しぬ')) == 'しん'
    assert (adjust_reading('たべた', 'たべる', 'たべる')) == 'たべた'
    assert (adjust_reading('カタカナ', 'カタカナ', 'かたかな')) == 'カタカナ'
    print("Passed.")


if __name__ == '__main__':
    main()
