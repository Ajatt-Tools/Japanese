# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Optional

try:
    from ..mecab_controller.kana_conv import is_kana_str
    from ..mecab_controller.unify_readings import replace_handakuten, literal_pronunciation as pr
except ImportError:
    from mecab_controller.kana_conv import is_kana_str
    from mecab_controller.unify_readings import replace_handakuten, literal_pronunciation as pr


def longest_kana_suffix(word: str) -> Optional[str]:
    for i in range(len(word)):
        if is_kana_str(substr := word[i:]):
            return substr


def is_inflected(headword: str, reading: str) -> bool:
    """
    Test if a reading of a verb/adjective is inflected, e.g. 臭くて, 臭かった.
    A reading is inflected if the word's kana ending isn't equal to the reading's ending.
    """
    headword, reading = replace_handakuten(headword), replace_handakuten(reading)
    return bool(
        (kana_suffix := longest_kana_suffix(headword))
        and pr(kana_suffix) != pr(reading[-len(kana_suffix):])
    )


def main():
    assert longest_kana_suffix("分かる") == "かる"
    assert longest_kana_suffix("綺麗") is None
    assert is_inflected("分かる", "わかる") is False
    assert is_inflected("臭い", "くさい") is False
    assert is_inflected("分かる", "わかった") is True
    assert is_inflected("綺麗", "きれい") is False
    assert is_inflected("産気づく", "さんけずく") is False
    assert is_inflected("ひらがな", "ヒラカ゚ナ") is False
    assert is_inflected("ひらがな", "ヒラカ゚ナオ") is True
    assert is_inflected("れんご", "レンコ゚") is False
    assert is_inflected("雇う", "やとう") is False
    print("Ok.")


if __name__ == '__main__':
    main()
