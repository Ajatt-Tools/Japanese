# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import itertools

import pytest

from japanese.mecab_controller import MecabController, to_katakana
from japanese.pitch_accents.acc_dict_mgr import AccentDictManager
from japanese.pitch_accents.accent_lookup import AccentLookup
from tests.no_anki_config import NoAnkiConfigView


@pytest.fixture(scope="session")
def acc_dict_mgr() -> AccentDictManager:
    acc_dict = AccentDictManager()
    acc_dict.reload_on_main()
    return acc_dict


@pytest.fixture(scope="session")
def lookup(acc_dict_mgr: AccentDictManager) -> AccentLookup:
    cfg = NoAnkiConfigView()
    mecab = MecabController(verbose=False, cache_max_size=cfg.cache_lookups)
    lookup = AccentLookup(acc_dict_mgr, cfg, mecab)
    return lookup


@pytest.mark.parametrize(
    "test_input,expected",
    [("聞かせて戻って", ("聞く", "戻る")), ("経緯と国境", ("経緯", "国境"))],
)
def test_accent_lookup(lookup: AccentLookup, test_input, expected) -> None:
    result = lookup.get_pronunciations(test_input)
    for item in expected:
        assert item in result


@pytest.mark.parametrize(
    "word,order",
    [("経緯", ("ケイイ", "イキサツ")), ("国境", ("コッキョウ", "クニザカイ")), ("私", ("わたし", "あたし"))],
)
def test_acc_dict(acc_dict_mgr: AccentDictManager, word, order) -> None:
    entries = acc_dict_mgr.lookup(word)
    assert entries
    reading_to_idx = {entry.katakana_reading: idx for idx, entry in enumerate(entries)}
    for higher_order, lower_order in itertools.pairwise(order):
        assert reading_to_idx[to_katakana(higher_order)] < reading_to_idx[to_katakana(lower_order)]


def test_missing_key(acc_dict_mgr: AccentDictManager) -> None:
    assert acc_dict_mgr.lookup("missing") is None
    assert acc_dict_mgr.lookup("") is None
