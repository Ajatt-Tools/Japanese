# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.helpers.inflections import is_inflected, longest_kana_suffix


@pytest.mark.parametrize(
    "expression, suffix",
    [
        ("分かる", "かる"),
        ("弄ばれてしまった", "ばれてしまった"),
        ("綺麗", ""),
        ("しまった", "しまった"),
        ("", ""),
    ],
)
def test_longest_kana_suffix(expression: str, suffix: str) -> None:
    assert longest_kana_suffix(expression) == suffix


@pytest.mark.parametrize(
    "headword, reading, answer",
    [
        ("分かる", "わかる", False),
        ("臭い", "くさい", False),
        ("綺麗", "きれい", False),
        ("産気づく", "さんけずく", False),
        ("ひらがな", "ヒラカ゚ナ", False),
        ("れんご", "レンコ゚", False),
        ("雇う", "やとう", False),
        ("ひらがな", "ヒラカ゚ナオ", True),
        ("分かる", "わかった", True),
    ],
)
def test_is_inflected(headword: str, reading: str, answer: bool) -> None:
    assert is_inflected(headword, reading) is answer
