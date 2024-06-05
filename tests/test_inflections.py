# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.helpers.inflections import is_inflected, longest_kana_suffix


def test_longest_kana_suffix() -> None:
    assert longest_kana_suffix("分かる") == "かる"
    assert longest_kana_suffix("綺麗") is None


def test_is_inflected() -> None:
    assert is_inflected("分かる", "わかる") is False
    assert is_inflected("臭い", "くさい") is False
    assert is_inflected("綺麗", "きれい") is False
    assert is_inflected("産気づく", "さんけずく") is False
    assert is_inflected("ひらがな", "ヒラカ゚ナ") is False
    assert is_inflected("れんご", "レンコ゚") is False
    assert is_inflected("雇う", "やとう") is False
    assert is_inflected("ひらがな", "ヒラカ゚ナオ") is True
    assert is_inflected("分かる", "わかった") is True
