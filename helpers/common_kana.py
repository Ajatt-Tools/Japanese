# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

def adjust_reading(raw_word: str, headword: str, headword_reading: str):
    if headword == headword_reading:
        return raw_word
    idx_headword, idx_reading = len(headword), len(headword_reading)
    try:
        while headword[idx_headword - 1] == headword_reading[idx_reading - 1]:
            idx_headword -= 1
            idx_reading -= 1
    except IndexError:
        return raw_word
    return headword_reading[:idx_reading] + raw_word[idx_headword:]


def main():
    print(adjust_reading('跪いた', '跪く', 'ひざまずく'))
    print(adjust_reading('安くなかった', '安い', 'やすい'))
    print(adjust_reading('繋りたい', '繋る', 'つながる'))
    print(adjust_reading('言い方', '言い方', 'いいかた'))
    print(adjust_reading('やり遂げさせられない', 'やり遂げる', 'やりとげる'))
    print(adjust_reading('死ん', '死ぬ', 'しぬ'))
    print(adjust_reading('たべた', 'たべる', 'たべる'))


if __name__ == '__main__':
    main()
