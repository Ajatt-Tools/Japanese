# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
import re
from collections.abc import Sequence

import pytest

from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.furigana.gen_furigana import FuriganaGen
from japanese.helpers.profiles import ColorCodePitchFormat
from japanese.helpers.tokens import HTML_AND_MEDIA_REGEX, clean_furigana
from japanese.mecab_controller import MecabController, to_katakana
from japanese.pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from japanese.pitch_accents.accent_lookup import AccentLookup
from playground.utils import NoAnkiConfigView
from tests.conftest import (
    tmp_db_connection,
    tmp_sqlite3_db_path,
    tmp_upd_file,
    tmp_user_accents_file,
)
from tests.no_anki_config import no_anki_config

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


def furigana_to_word_seq(furigana_output: str) -> list[str]:
    return [part for part in re.split(HTML_AND_MEDIA_REGEX, clean_furigana(furigana_output)) if part]


class TestAccDictLookup:
    @pytest.fixture(scope="class")
    def acc_dict_mgr(
        self, tmp_sqlite3_db_path: pathlib.Path, tmp_upd_file: pathlib.Path, tmp_user_accents_file: pathlib.Path
    ) -> AccentDictManager2:
        acc_dict = AccentDictManager2(tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file)
        acc_dict.ensure_dict_ready_on_main()
        return acc_dict

    @pytest.fixture(scope="class")
    def lookup(
        self,
        no_anki_config: NoAnkiConfigView,
    ) -> AccentLookup:
        cfg = no_anki_config
        mecab = MecabController(verbose=False, cache_max_size=cfg.cache_lookups)
        lookup = AccentLookup(cfg, mecab)
        return lookup

    @pytest.fixture(scope="class")
    def fgen(self, no_anki_config: NoAnkiConfigView, lookup: AccentLookup) -> FuriganaGen:
        cfg = no_anki_config
        fgen = FuriganaGen(cfg, lookup)
        return fgen

    @pytest.mark.parametrize(
        "word, order",
        [("経緯", ("ケイイ", "イキサツ")), ("国境", ("コッキョウ", "クニザカイ")), ("私", ("わたし", "あたし"))],
    )
    def test_acc_dict(self, acc_dict_mgr: AccentDictManager2, word: str, order: Sequence[str]) -> None:
        """
        More frequent readings should come first.
        """
        assert acc_dict_mgr.is_ready()
        entries = acc_dict_mgr.lookup(word)
        assert entries
        reading_to_idx = {entry.katakana_reading: idx for idx, entry in enumerate(entries)}
        for higher_order, lower_order in pairwise(order):
            assert reading_to_idx[to_katakana(higher_order)] < reading_to_idx[to_katakana(lower_order)]

    def test_missing_key(self, acc_dict_mgr: AccentDictManager2) -> None:
        assert acc_dict_mgr.is_ready()
        assert not acc_dict_mgr.lookup("missing")
        assert not acc_dict_mgr.lookup("")

    @pytest.mark.parametrize(
        "test_input, expected",
        [("聞かせて戻って", ("聞く", "戻る")), ("経緯と国境", ("経緯", "国境"))],
    )
    def test_accent_lookup(
        self, tmp_db_connection: Sqlite3Buddy, lookup: AccentLookup, test_input: str, expected: Sequence[str]
    ) -> None:
        result = lookup.with_new_buddy(tmp_db_connection).get_pronunciations(test_input)
        for item in expected:
            assert item in result

    @pytest.mark.parametrize(
        "sentence, expected",
        [
            ("随分思い切ったなぁとか思ってたけど", ["随分", "思い切った", "なぁとか", "思ってた", "けど"]),
            ("倒しただけだろ", ["倒した", "だけだろ"]),
            ("弄ばれてしまった", ["弄ばれて", "しまった"]),
            ("熱くなった", ["熱く", "なった"]),
            ("疑わなかったの", ["疑わなかった", "の"]),
            ("赤くなかった", ["赤く", "なかった"]),
            ("嬉しくない", ["嬉しく", "ない"]),
            ("しか知らなかった", ["しか", "知らなかった"]),
            ("そんなに忙しくなかったんでしょ", ["そんなに", "忙しく", "なかったんでしょ"]),
            ("判断は間違っていなかった", ["判断", "は", "間違って", "いなかった"]),
            ("お前はもう死んでいる", ["お前", "は", "もう", "死んでいる"]),
            ("長けておる", ["長けて", "おる"]),
            ("借金も抱えてたじゃない", ["借金", "も", "抱えてた", "じゃない"]),
            ("あるでしょうし", ["ある", "でしょうし"]),
            ("思ったんでしょう", ["思った", "んでしょう"]),
            ("出たな", ["出た", "な"]),
            ("ボーイフレンドを見つけたらしい", ["ボーイフレンド", "を", "見つけた", "らしい"]),
            ("死なないでくれ", ["死なないで", "くれ"]),
            ("下に入れてくれ。", ["下", "に", "入れて", "くれ", "。"]),
            ("僕はそれに立ち会ったにすぎません", ["僕", "は", "それ", "に", "立ち会った", "に", "すぎません"]),
            ("推奨できません", ["推奨", "できません"]),
            ("分かりませんが", ["分かりません", "が"]),
            ("感情的になったら", ["感情的", "に", "なったら"]),
            ("ございました", ["ございました"]),
            ("低くみる", ["低く", "みる"]),
            ("〇は出来ん", ["〇は", "出来ん"]),
            ("〇はできん", ["〇は", "できん"]),
            ("〇はできんぞ", ["〇は", "できん", "ぞ"]),
            ("掠れば", ["掠れば"]),
            ("楽しませてくれればいい", ["楽しませて", "くれれば", "いい"]),
            ("放っておけない", ["放って", "おけない"]),
            ("塗り込まれているようです", ["塗り", "込まれている", "よう", "です"]),
            ("謝らないでほしい。", ["謝らないで", "ほしい", "。"]),
        ],
    )
    def test_attach_rules(
        self, tmp_db_connection: Sqlite3Buddy, fgen: FuriganaGen, sentence: str, expected: Sequence[str]
    ) -> None:
        text = fgen.with_new_buddy(tmp_db_connection).generate_furigana(
            sentence,
            output_format=ColorCodePitchFormat.attributes,
        )
        assert furigana_to_word_seq(text) == expected

    @pytest.mark.parametrize(
        "sentence, expected",
        [
            ("一人暮らし", "一人暮[ひとりぐ]らし"),
            ("掏摸に用心しなさい", "掏摸[すり]に 用心[ようじん]しなさい"),
            (
                "三色チーズ牛丼の特盛に温玉付きをお願いします",
                "三色[さんしき]チーズ 牛丼[ぎゅうどん]の 特盛[とくもり]に 温玉[おんたま] 付[つ]きをお 願[ねが]いします",
            ),
        ],
    )
    def test_furigana(self, tmp_db_connection: Sqlite3Buddy, fgen: FuriganaGen, sentence: str, expected: str) -> None:
        text = fgen.with_new_buddy(tmp_db_connection).generate_furigana(
            sentence,
            output_format=ColorCodePitchFormat(0),
        )
        assert text == expected

    @pytest.mark.parametrize(
        "readings, unique",
        [
            (["ジュウガツ", "ジュウガツ", "ジューガツ", "ジューガツ"], ["ジュウガツ"]),
            (
                ["リュウセンガタ", "リューセンケイ", "リューセンガタ", "リュウセンケイ"],
                ["リュウセンガタ", "リュウセンケイ"],
            ),
        ],
    )
    def test_unique_readings(self, fgen: FuriganaGen, readings: list[str], unique: list[str]) -> None:
        assert fgen.unique_readings(readings) == unique
