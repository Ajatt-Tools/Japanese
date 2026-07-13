# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

import pytest

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.entry_to_moras import Mora
from japanese.pitch_accents.svg_components import (
    Point,
    append_class_name,
    assemble_txt_content,
)
from japanese.pitch_accents.svg_graph_renderer import SvgGraphRenderer
from japanese.pitch_accents.svg_graph_types import PitchLevel, SvgMoraFlag
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from playground.utils import NoAnkiConfigView
from tests import DATA_DIR

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


def extract_group_class_names(svg: str) -> list[str]:
    """Extract CSS class names from all SVG group elements."""
    return re.findall(r'<g class="(?P<class_name>[^"]+)">', svg)


@pytest.mark.parametrize(
    "formatted_entry, svg_file_name",
    [(entry, f"test_{idx}.svg") for idx, entry in enumerate(TEST_ENTRIES)],
)
def test_make_svg(no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry, svg_file_name: str) -> None:
    svg_config = SvgPitchGraphOptionsConfigView(no_anki_config)
    svg_config.graph_font_name = "Noto Sans CJK JP"  # simplify
    maker = SvgPitchGraphMaker(options=svg_config)

    with open(DATA_DIR / svg_file_name, encoding="utf-8") as f:
        assert (
            f.read().strip() == maker.make_graph(formatted_entry).strip()
        ), f"generated content must match: {DATA_DIR / svg_file_name}"


@pytest.mark.parametrize("formatted_entry", TEST_ENTRIES)
def test_dictionary_path_group_is_named_lines(
    no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry
) -> None:
    """Dictionary SVGs use the shared 'lines' class for the pitch-contour group."""
    svg_config = SvgPitchGraphOptionsConfigView(no_anki_config)
    svg_config.graph_font_name = "Noto Sans CJK JP"
    maker = SvgPitchGraphMaker(options=svg_config)
    group_class_names = extract_group_class_names(maker.make_graph(formatted_entry))

    assert [class_name for class_name in group_class_names if class_name == "lines"] == ["lines"]
    assert [class_name for class_name in group_class_names if class_name == "paths"] == []


@pytest.mark.parametrize(
    "mora, expected_text",
    [
        (Mora(txt=["ア"], level=PitchLevel.high, flags=SvgMoraFlag.devoiced), "ア"),
    ],
)
def test_make_text_keeps_mora_api(no_anki_config: NoAnkiConfigView, mora: Mora, expected_text: str) -> None:
    """Public text rendering still accepts a Mora, not pre-rendered text."""
    svg_config = SvgPitchGraphOptionsConfigView(no_anki_config)
    maker = SvgGraphRenderer(options=svg_config)
    text = assemble_txt_content(mora, reading_format=svg_config.reading_format, tspan_dx=svg_config.tspan_dx)
    assert not mora.is_trailing()
    assert (
        maker.make_text_element(text, Point.new(x=1, y=2), class_attr=append_class_name(mora.flags), dx=3)
        == f'<text class="devoiced" fill="black" font-size="{svg_config.font_size:.1f}px" '
        f'letter-spacing="{svg_config.letter_spacing:.1f}px" x="1" y="2" dx="3">{expected_text}</text>'
    )


def test_heiban_trailing_circle_has_fill_none(no_anki_config: NoAnkiConfigView) -> None:
    """Heiban dictionary graphs add a trailing hollow circle for following particles."""
    svg_config = SvgPitchGraphOptionsConfigView(no_anki_config)
    svg_config.graph_font_name = "Noto Sans CJK JP"
    maker = SvgPitchGraphMaker(options=svg_config)

    svg = maker.make_graph(TEST_ENTRIES[0])

    assert '<circle class="trail" fill="none" stroke="gray"' in svg
