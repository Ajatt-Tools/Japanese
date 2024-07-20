# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from tests import DATA_DIR
from tests.no_anki_config import NoAnkiConfigView

TEST_ENTRIES = (
    FormattedEntry(
        "ジンロウ",
        "<low_rise>ジ</low_rise><high>ンロウ</high>",
        "0",
    ),
    FormattedEntry(
        "スイソウガク",
        "<low_rise>ス</low_rise><high_drop>イソ</high_drop><low>ーカ<nasal>&#176;</nasal>ク</low>",
        "3",
    ),
    FormattedEntry(
        "ツケヒモ",
        "<low_rise><devoiced>ツ</devoiced></low_rise><high>ケヒモ</high>",
        "0",
    ),
    FormattedEntry(
        "ニジュウヨジカン",
        "<high_drop>ニ</high_drop><low>ジュー</low>・<low_rise>ヨ</low_rise><high_drop>ジ</high_drop><low>カン</low>",
        "1+2",
    ),
    FormattedEntry(
        "ニ",
        "<low_rise>ニ</low_rise>",
        "0",
    ),
    FormattedEntry(
        "ヨ",
        "<high_drop>ヨ</high_drop>",
        "1",
    ),
    FormattedEntry(
        "オトート",
        "<low_rise>オ</low_rise><high_drop>トート</high_drop>",
        "4",
    ),
)


@pytest.mark.parametrize(
    "formatted_entry, svg_file_name",
    [(entry, f"test_{idx}.svg") for idx, entry in enumerate(TEST_ENTRIES)],
)
def test_make_svg(formatted_entry: FormattedEntry, svg_file_name: str) -> None:
    config = NoAnkiConfigView()
    svg_config = SvgPitchGraphOptionsConfigView(config)
    maker = SvgPitchGraphMaker(options=svg_config)

    with open(DATA_DIR / svg_file_name, encoding="utf-8") as f:
        assert f.read().strip() == maker.make_graph(formatted_entry).strip(), "generated content must match"
