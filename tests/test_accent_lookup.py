import pytest

from japanese.mecab_controller import MecabController
from japanese.pitch_accents.acc_dict_mgr import AccentDictManager
from japanese.pitch_accents.accent_lookup import AccentLookup
from tests.no_anki_config import NoAnkiConfigView


@pytest.fixture
def lookup() -> AccentLookup:
    cfg = NoAnkiConfigView()
    mecab = MecabController(verbose=False, cache_max_size=cfg.cache_lookups)
    acc_dict = AccentDictManager()
    acc_dict.reload_on_main()
    lookup = AccentLookup(acc_dict, cfg, mecab)
    return lookup


def test_accent_lookup(lookup: AccentLookup) -> None:
    result = lookup.get_pronunciations("聞かせて戻って")
    assert "聞く" in result
    assert "戻る" in result
