# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    from ..mecab_controller import to_katakana
except ImportError:
    from mecab_controller import to_katakana

KANA_MAP = (
    ('けー', 'けい'),
    ('ぐー', 'ぐう'),
    ('ごー', 'ごう'),
    ('ずー', 'ずう'),
    ('ぞー', 'ぞう'),
    ('づー', 'づう'),
    ('どー', 'どう'),
    ('ぶー', 'ぶう'),
    ('ぼー', 'ぼう'),
    ('ぷー', 'ぷう'),
    ('ぽー', 'ぽう'),
    ('うー', 'うう'),
    ('おー', 'おう'),
    ('くー', 'くう'),
    ('こー', 'こう'),
    ('すー', 'すう'),
    ('そー', 'そう'),
    ('つー', 'つう'),
    ('とー', 'とう'),
    ('ぬー', 'ぬう'),
    ('のー', 'のう'),
    ('ふー', 'ふう'),
    ('ほー', 'ほう'),
    ('むー', 'むう'),
    ('もー', 'もう'),
    ('よー', 'よう'),
    ('るー', 'るう'),
    ('ろー', 'ろう'),
    ('ぅー', 'ぅう'),
    ('ぉー', 'ぉう'),
    ('ょー', 'ょう'),
    ('ゅー', 'ゅう'),
    ('ゆー', 'ゆう'),
    ('いー', 'いい'),
    ('ちー', 'ちい'),
    ('せー', 'せい'),
    ('じー', 'じい'),
    ('かー', 'かあ'),
    ('ゅー', 'ゅう'),
    ('ぜー', 'ぜい'),
    ('ほお', 'ほう'),
    ('どお', 'どう'),
    ('とお', 'とう'),
    ('おお', 'おう'),
    ('ずう', 'づう'),
    ('つず', 'つづ'),
    ('じ', 'ぢ'),
    ('ず', 'づ'),
    ('お', 'を'),
)
KANA_MAP = KANA_MAP + tuple((to_katakana(key), to_katakana(val)) for key, val in KANA_MAP)
KANA_MAP_REV = tuple((val, key) for key, val in KANA_MAP)


def unify_repr(reading: str, reverse: bool = False):
    """
    NHK database contains entries with redundant readings.
    They only differ by the use of 'ー' or kana characters that sound the same.
    Try to de-duplicate them.
    """
    vowels_map = KANA_MAP_REV if reverse else KANA_MAP

    for key, value in vowels_map:
        if key in reading:
            reading = reading.replace(key, value)
    return reading


def literal_pronunciation(text: str) -> str:
    for adjusted, normal in KANA_MAP:
        if normal in text:
            text = text.replace(normal, adjusted)
    text = to_katakana(text)
    return text


if __name__ == '__main__':
    print("Unified:")
    print(unify_repr('ひつよー'))
    print(unify_repr('ヒツヨー'))
    print("Reverse:")
    print(unify_repr('おはよう', reverse=True))
    print("Literal:")
    print(literal_pronunciation('がっこう'))
