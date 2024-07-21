# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Sequence

import pytest

from japanese.mecab_controller import MecabController, to_katakana
from japanese.pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from japanese.pitch_accents.accent_lookup import AccentLookup
from tests.no_anki_config import NoAnkiConfigView, no_anki_config
from tests.sqlite3_buddy import tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file

try:
    from itertools import pairwise
except ImportError:
    # python 3.9 doesn't have pairwise
    def pairwise(iterable):
        # https://docs.python.org/3/library/itertools.html#itertools.pairwise
        iterator = iter(iterable)
        a = next(iterator, None)
        for b in iterator:
            yield a, b
            a = b


class TestAccDictLookup:
    @pytest.fixture(scope="class")
    def acc_dict_mgr(self, tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file) -> AccentDictManager2:
        acc_dict = AccentDictManager2(tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file)
        acc_dict.ensure_dict_ready_on_main()
        return acc_dict

    @pytest.fixture(scope="class")
    def lookup(self, no_anki_config: NoAnkiConfigView, acc_dict_mgr: AccentDictManager2) -> AccentLookup:
        cfg = no_anki_config
        mecab = MecabController(verbose=False, cache_max_size=cfg.cache_lookups)
        lookup = AccentLookup(acc_dict_mgr, cfg, mecab)
        return lookup

    @pytest.mark.parametrize(
        "test_input, expected",
        [("聞かせて戻って", ("聞く", "戻る")), ("経緯と国境", ("経緯", "国境"))],
    )
    def test_accent_lookup(self, lookup: AccentLookup, test_input, expected) -> None:
        result = lookup.get_pronunciations(test_input)
        for item in expected:
            assert item in result

    @pytest.mark.parametrize(
        "word, order",
        [("経緯", ("ケイイ", "イキサツ")), ("国境", ("コッキョウ", "クニザカイ")), ("私", ("わたし", "あたし"))],
    )
    def test_acc_dict(self, acc_dict_mgr: AccentDictManager2, word: str, order: Sequence[str]) -> None:
        assert acc_dict_mgr.is_ready()
        entries = acc_dict_mgr.lookup(word)
        assert entries
        reading_to_idx = {entry.katakana_reading: idx for idx, entry in enumerate(entries)}
        for higher_order, lower_order in pairwise(order):
            assert reading_to_idx[to_katakana(higher_order)] < reading_to_idx[to_katakana(lower_order)]

    def test_missing_key(self, acc_dict_mgr: AccentDictManager2) -> None:
        assert acc_dict_mgr.is_ready()
        assert acc_dict_mgr.lookup("missing") is None
        assert acc_dict_mgr.lookup("") is None
