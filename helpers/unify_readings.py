# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

KANA_MAP = (
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
    ('つづ', 'つず'),
    ('ほお', 'ほう'),
    ('とお', 'とう'),
    ('おお', 'おう'),
    ('づう', 'ずう'),
    ('ぢ', 'じ'),
    ('づ', 'ず'),
)

KANA_MAP_REV = ((val, key) for (key, val) in KANA_MAP)


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


if __name__ == '__main__':
    print(unify_repr('ひつよー'))
    print(unify_repr('おはよう', reverse=True))
