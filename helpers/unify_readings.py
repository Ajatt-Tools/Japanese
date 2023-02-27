# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    from ..mecab_controller import to_katakana
except ImportError:
    from mecab_controller import to_katakana

EQUIVALENT_SOUNDS = {
    'おおう': 'おーう',
    'じゃあ': 'じゃー',
    'じょう': 'じょー',
    'れい': 'れー',
    'めい': 'めー',
    'べい': 'べー',
    'けい': 'けー',
    'ぐう': 'ぐー',
    'ごう': 'ごー',
    'ずう': 'ずー',
    'づう': 'ずー',
    'づー': 'ずー',
    'ぞう': 'ぞー',
    'どう': 'どー',
    'どお': 'どー',
    'ぶう': 'ぶー',
    'ぼう': 'ぼー',
    'ぷう': 'ぷー',
    'ぽう': 'ぽー',
    'うう': 'うー',
    'おう': 'おー',
    'おお': 'おー',
    'くう': 'くー',
    'こう': 'こー',
    'すう': 'すー',
    'そう': 'そー',
    'つう': 'つー',
    'とう': 'とー',
    'とお': 'とー',
    'こお': 'こー',
    'ぬう': 'ぬー',
    'のう': 'のー',
    'ふう': 'ふー',
    'ほう': 'ほー',
    'ほお': 'ほー',
    'むう': 'むー',
    'もう': 'もー',
    'よう': 'よー',
    'るう': 'るー',
    'ろう': 'ろー',
    'ぅう': 'ぅー',
    'ぉう': 'ぉー',
    'ょう': 'ょー',
    'ゆう': 'ゆー',
    'いい': 'いー',
    'ちい': 'ちー',
    'せい': 'せー',
    'じい': 'じー',
    'かあ': 'かー',
    'ゅう': 'ゅー',
    'ぜい': 'ぜー',
    'つづ': 'つず',
    'よお': 'よー',
    'ねえ': 'ねー',
    'にい': 'にー',
    'ばあ': 'ばー',
    'らあ': 'らー',
    'ごお': 'ごー',
    'ぢ': 'じ',
    'づ': 'ず',
    'を': 'お',
}
EQUIVALENT_SOUNDS |= {to_katakana(key): to_katakana(val) for key, val in EQUIVALENT_SOUNDS.items()}


def unify_repr(reading: str):
    """
    NHK database contains entries with redundant readings.
    They only differ by the use of 'ー' or kana characters that sound the same.
    Try to de-duplicate them.
    """
    for key, value in EQUIVALENT_SOUNDS.items():
        if key in reading:
            reading = reading.replace(key, value)
    return reading


def literal_pronunciation(text: str) -> str:
    return to_katakana(unify_repr(text))


def test():
    assert unify_repr('おおうなばら') == 'おーうなばら'
    assert unify_repr('おはよう') == 'おはよー'
    assert unify_repr('おお') == 'おー'
    assert unify_repr('よじょうはん') == 'よじょーはん'
    assert literal_pronunciation('がっこう') == 'ガッコー'


if __name__ == '__main__':
    test()
