# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

import pytest

from japanese.pitch_accents.colors import SvgGraphClassName, SvgGraphColorMode
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.entry_to_moras import Mora
from japanese.pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from japanese.pitch_accents.svg_components import (
    Point,
    append_class_name,
    assemble_txt_content,
)
from japanese.pitch_accents.svg_graph_renderer import SvgGraphRenderer
from japanese.pitch_accents.svg_graph_types import PitchLevel, SvgMoraFlag
from playground.utils import NoAnkiConfigView
from tests.consts import DATA_DIR

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
    maker = FormattedEntryToSvgAdapter(no_anki_config)

    reference_file_path = DATA_DIR / "formatted_entry_graphs" / svg_file_name
    reference = reference_file_path.read_text(encoding="utf-8").strip()
    graph = maker.make_graph(formatted_entry).strip()
    assert graph == reference, f"generated content must match: {reference_file_path}"


@pytest.mark.parametrize("formatted_entry", TEST_ENTRIES)
def test_dictionary_path_group_is_named_lines(
    no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry
) -> None:
    """Dictionary SVGs use the shared 'lines' class for the pitch-contour group."""
    maker = FormattedEntryToSvgAdapter(no_anki_config)
    group_class_names = extract_group_class_names(maker.make_graph(formatted_entry))

    assert [class_name for class_name in group_class_names if class_name == "lines"] == ["lines"]
    assert [class_name for class_name in group_class_names if class_name == "paths"] == []


@pytest.mark.parametrize(
    "mora, expected_text",
    [
        (Mora(txt=["ア"], level=PitchLevel.high, flags=SvgMoraFlag.devoiced), "ア"),
    ],
)
def test_renderer_make_text_element(no_anki_config: NoAnkiConfigView, mora: Mora, expected_text: str) -> None:
    """Renderer text elements keep class attributes and formatted coordinates."""
    maker = SvgGraphRenderer(no_anki_config)
    text = assemble_txt_content(
        mora,
        reading_format=no_anki_config.svg_graphs.reading_format,
        tspan_dx=no_anki_config.svg_graphs.tspan_dx,
        nasal_color="red",
    )
    assert not mora.is_trailing()
    assert (
        maker.make_text_element(
            text,
            Point.new(x=1, y=2),
            class_attr=append_class_name(mora.flags),
            dx=3,
            class_name=SvgGraphClassName.heiban,
        )
        == f'<text class="devoiced" fill="black" font-size="{no_anki_config.svg_graphs.font_size:.1f}px" '
        f'letter-spacing="{no_anki_config.svg_graphs.letter_spacing:.1f}px" x="1" y="2" dx="3">{expected_text}</text>'
    )


@pytest.mark.parametrize("formatted_entry", [TEST_ENTRIES[0]])
def test_heiban_trailing_circle_has_fill_none(
    no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry
) -> None:
    """Heiban dictionary graphs add a trailing hollow circle for following particles."""
    maker = FormattedEntryToSvgAdapter(no_anki_config)

    svg = maker.make_graph(formatted_entry)

    assert svg.count('<circle class="trail" fill="none" stroke="gray"') == 1


@pytest.mark.parametrize(
    "formatted_entry, expected_color",
    [
        (TEST_ENTRIES[0], "#005ce6"),
        (TEST_ENTRIES[1], "#ff6207"),
        (TEST_ENTRIES[5], "#e60000"),
    ],
)
def test_svg_attributes_color_mode(formatted_entry: FormattedEntry, expected_color: str) -> None:
    """SVG attribute color mode writes role colors directly into SVG markup."""
    no_anki_config = NoAnkiConfigView()
    no_anki_config.svg_graphs["color_mode"] = SvgGraphColorMode.svg_attributes.name

    svg = FormattedEntryToSvgAdapter(no_anki_config).make_graph(formatted_entry)

    assert f'fill="{expected_color}" stroke="{expected_color}"' in svg


@pytest.mark.parametrize(
    "formatted_entry, include_text, expected_text_group_count",
    [
        (TEST_ENTRIES[0], False, 0),
        (TEST_ENTRIES[0], True, 1),
    ],
)
def test_text_group_matches_text_visibility(
    formatted_entry: FormattedEntry,
    include_text: bool,
    expected_text_group_count: int,
) -> None:
    """Text group markup is emitted only when kana text is visible."""
    no_anki_config = NoAnkiConfigView()
    no_anki_config.svg_graphs["include_text"] = include_text
    maker = FormattedEntryToSvgAdapter(no_anki_config)
    svg = maker.make_graph(formatted_entry)
    assert svg.count('<g class="text">') == expected_text_group_count


@pytest.mark.parametrize(
    "formatted_entry, graph_horizontal_padding, size_unit, graph_height, expected_fragments",
    [
        (
            TEST_ENTRIES[0],
            50,
            40,
            80,
            ('viewBox="0 0 350 210"', 'cx="90.000" cy="120.000"', 'cy="40.000"'),
        ),
    ],
)
def test_renderer_uses_mutated_options(
    formatted_entry: FormattedEntry,
    graph_horizontal_padding: int,
    size_unit: int,
    graph_height: int,
    expected_fragments: tuple[str, str, str],
) -> None:
    """Renderer geometry is computed from current options, not stale cached values."""
    no_anki_config = NoAnkiConfigView()
    maker = FormattedEntryToSvgAdapter(no_anki_config)
    before = maker.make_graph(formatted_entry)
    no_anki_config.svg_graphs.update({
        "graph_horizontal_padding": graph_horizontal_padding,
        "size_unit": size_unit,
        "graph_height": graph_height,
    })

    after = maker.make_graph(formatted_entry)

    assert before != after
    assert all(fragment in after for fragment in expected_fragments)
