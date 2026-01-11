# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from playground.utils import NoAnkiConfigView
from tests import DATA_DIR
from tests.no_anki_config import no_anki_config

TEST_ENTRIES = (
    FormattedEntry(
        "塵労",
        "ジンロウ",
        "<low_rise>ジ</low_rise><high>ンロウ</high>",
        "0",
    ),
    FormattedEntry(
        "吹奏楽",
        "スイソウガク",
        "<low_rise>ス</low_rise><high_drop>イソ</high_drop><low>ー<nasal>カ<handakuten>&#176;</handakuten></nasal>ク</low>",
        "3",
    ),
    FormattedEntry(
        "付け紐",
        "ツケヒモ",
        "<low_rise><devoiced>ツ</devoiced></low_rise><high>ケヒモ</high>",
        "0",
    ),
    FormattedEntry(
        "二十四時間",
        "ニジュウヨジカン",
        "<high_drop>ニ</high_drop><low>ジュー</low>・<low_rise>ヨ</low_rise><high_drop>ジ</high_drop><low>カン</low>",
        "1+2",
    ),
    FormattedEntry(
        "に",
        "ニ",
        "<low_rise>ニ</low_rise>",
        "0",
    ),
    FormattedEntry(
        "よ",
        "ヨ",
        "<high_drop>ヨ</high_drop>",
        "1",
    ),
    FormattedEntry(
        "弟",
        "オトート",
        "<low_rise>オ</low_rise><high_drop>トート</high_drop>",
        "4",
    ),
    FormattedEntry(
        "淑女",
        "シュクジョ",
        "<high_drop><devoiced>シ</devoiced>ュ</high_drop><low>クジョ</low>",
        "1",
    ),
    FormattedEntry(
        "悪逆",
        "アクギャク",
        "<low_rise>ア</low_rise><high>ク<nasal>キ<handakuten>&#176;</handakuten></nasal>ャク</high>",
        "0",
    ),
)


@pytest.mark.parametrize(
    "formatted_entry, svg_file_name",
    [(entry, f"test_{idx}.svg") for idx, entry in enumerate(TEST_ENTRIES)],
)
def test_make_svg(no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry, svg_file_name: str) -> None:
    svg_config = SvgPitchGraphOptionsConfigView(no_anki_config)
    maker = SvgPitchGraphMaker(options=svg_config)

    with open(DATA_DIR / svg_file_name, encoding="utf-8") as f:
        assert (
            f.read().strip() == maker.make_graph(formatted_entry).strip()
        ), f"generated content must match: {DATA_DIR / svg_file_name}"
