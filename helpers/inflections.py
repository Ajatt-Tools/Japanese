# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Optional

try:
    from ..mecab_controller import is_kana_str
    from .unify_readings import literal_pronunciation
except ImportError:
    from mecab_controller import is_kana_str
    from unify_readings import literal_pronunciation


def longest_kana_suffix(word: str) -> Optional[str]:
    for i in range(len(word)):
        if is_kana_str(substr := word[i:]):
            return substr


def is_inflected(headword: str, reading: str) -> bool:
    """
    Test if a reading of a verb/adjective is inflected, e.g. 臭くて, 臭かった.
    A reading is inflected if the word's kana ending isn't equal to the reading's ending.
    """
    return bool(
        (kana_suffix := longest_kana_suffix(headword))
        and literal_pronunciation(kana_suffix) != literal_pronunciation(reading[-len(kana_suffix):])
    )


def main():
    assert longest_kana_suffix("分かる") == "かる"
    assert longest_kana_suffix("綺麗") is None
    assert is_inflected("分かる", "わかる") is False
    assert is_inflected("臭い", "くさい") is False
    assert is_inflected("分かる", "わかった") is True
    assert is_inflected("綺麗", "きれい") is False
    assert is_inflected("産気づく", "さんけずく") is False
    print("Ok.")


if __name__ == '__main__':
    main()
