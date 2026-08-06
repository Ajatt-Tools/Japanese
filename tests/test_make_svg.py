# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json
import pathlib
import re
import typing
from collections.abc import Sequence

import pytest

from japanese.pitch_accents.colors import SvgGraphClassName, SvgGraphColorMode
from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.entry_to_moras import Mora
from japanese.pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from japanese.pitch_accents.svg_components import (
    Line,
    Point,
    SvgBlackAndWhiteRole,
    append_class_name,
    assemble_txt_content,
    lookup_component_color,
)
from japanese.pitch_accents.svg_graph_renderer import (
    SvgGraphRenderer,
    connector_css_class,
    is_accented_particle,
)
from japanese.pitch_accents.svg_graph_types import (
    ConnectToPrevious,
    PitchLevel,
    SvgGraph,
    SvgGraphMora,
    SvgGraphWord,
    SvgMoraFlag,
)
from playground.utils import NoAnkiConfigView
from tests.consts import DATA_DIR
from tests.helpers import extract_group_class_names, make_fresh_config

RE_HEX_COLOR: typing.Final = re.compile(r"#[0-9a-fA-F]{6}\b")
RE_CSS_CLASS_REFERENCE: typing.Final = re.compile(r"\.(?P<class_name>[a-zA-Z_][a-zA-Z0-9_]*)")
PROJECT_ROOT: typing.Final = pathlib.Path(__file__).resolve().parents[1]
CONFIG_PATH: typing.Final = PROJECT_ROOT / "japanese" / "config.json"
PITCH_GRAPH_CSS_PATH: typing.Final = PROJECT_ROOT / "japanese" / "web" / "ajt_pitch_graph.css"

TEST_ENTRIES: typing.Final = (
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


class StartsWithTrailingMoraScenario(typing.NamedTuple):
    """Scenario for SvgGraphWord.starts_with_trailing_mora."""

    moras: Sequence[SvgGraphMora]
    expected: bool


STARTS_WITH_TRAILING_MORA_SCENARIOS: typing.Final[dict[str, StartsWithTrailingMoraScenario]] = {
    "empty": StartsWithTrailingMoraScenario(moras=(), expected=False),
    "first_trailing": StartsWithTrailingMoraScenario(
        moras=(SvgGraphMora(text="", level=PitchLevel.low, flags=SvgMoraFlag.trailing),), expected=True
    ),
    "first_normal": StartsWithTrailingMoraScenario(
        moras=(SvgGraphMora(text="ア", level=PitchLevel.low),), expected=False
    ),
}


@pytest.mark.parametrize(
    "formatted_entry, svg_file_name",
    [(entry, f"test_{idx}.svg") for idx, entry in enumerate(TEST_ENTRIES)],
)
def test_make_svg(no_anki_config: NoAnkiConfigView, formatted_entry: FormattedEntry, svg_file_name: str) -> None:
    """Dictionary-entry SVG output matches the checked-in full SVG references."""
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


def test_single_mora_artist_graph_omits_lines_group(no_anki_config: NoAnkiConfigView) -> None:
    """A Pitch Artist graph of single-mora sections has circles/text but no lines group.

    A single mora has no pitch contour (a line needs two points), so the
    "lines" group is intentionally omitted while circles and text remain.
    """
    graph = SvgGraph(
        sections=(
            SvgGraphWord(
                class_name=SvgGraphClassName.heiban,
                moras=(SvgGraphMora(text="ア", level=PitchLevel.high),),
                is_particle=False,
                connect_to_previous=ConnectToPrevious.none,
            ),
        ),
        outer_class_name=None,
    )

    svg = SvgGraphRenderer(no_anki_config).render_graph(graph)

    assert '<g class="lines">' not in svg
    assert '<g class="circles">' in svg
    assert '<g class="text">' in svg


def test_renderer_make_text_element(no_anki_config: NoAnkiConfigView) -> None:
    """Renderer text elements keep class attributes and formatted coordinates."""
    maker = SvgGraphRenderer(no_anki_config)
    mora = Mora(txt=["ア"], level=PitchLevel.high, flags=SvgMoraFlag.devoiced)
    text = assemble_txt_content(
        mora,
        reading_format=no_anki_config.svg_graphs.reading_format,
        tspan_dx=no_anki_config.svg_graphs.tspan_dx,
        nasal_color=SvgBlackAndWhiteRole.nasal.value,
    )
    assert not mora.is_trailing, "mora can't be trailing"
    expected_color = lookup_component_color(no_anki_config, SvgBlackAndWhiteRole.word, SvgGraphClassName.heiban)
    assert (
        maker.make_text_element(
            text,
            pos=Point.new(x=1, y=2),
            class_attr=append_class_name(SvgMoraFlag.devoiced),
            dx=3,
            text_color=expected_color,
        )
        == f'<text class="devoiced" fill="{expected_color}" font-size="{no_anki_config.svg_graphs.font_size:.1f}px" '
        f'letter-spacing="{no_anki_config.svg_graphs.letter_spacing:.1f}px" x="1" y="2" dx="3">ア</text>'
    )


@pytest.mark.parametrize(
    "scenario", STARTS_WITH_TRAILING_MORA_SCENARIOS.values(), ids=list(STARTS_WITH_TRAILING_MORA_SCENARIOS.keys())
)
def test_starts_with_trailing_mora(scenario: StartsWithTrailingMoraScenario) -> None:
    """SvgGraphWord reports whether its first mora is a trailing marker."""
    word = SvgGraphWord(
        class_name=SvgGraphClassName.heiban,
        moras=scenario.moras,
        is_particle=False,
        connect_to_previous=ConnectToPrevious.none,
    )

    assert word.starts_with_trailing_mora is scenario.expected


def test_line_end_point_raises_before_end_is_set(no_anki_config: NoAnkiConfigView) -> None:
    """Line.end_point rejects incomplete lines."""
    with pytest.raises(ValueError):
        Line(no_anki_config, SvgGraphClassName.heiban).end_point


def test_line_adjust_to_radius_is_idempotent(no_anki_config: NoAnkiConfigView) -> None:
    """adjust_to_radius returns a copy, so repeated draws do not shift endpoints twice."""
    line = Line(no_anki_config, SvgGraphClassName.heiban).start_at(Point.new(x=0, y=0)).end_at(Point.new(x=10, y=0))

    assert line.adjust_to_radius().draw() == line.adjust_to_radius().draw()
    assert line.end_point == Point.new(x=10, y=0)


def make_word(class_name: SvgGraphClassName, *, is_particle: bool) -> SvgGraphWord:
    """Return a minimal one-mora graph word for connector class tests."""
    return SvgGraphWord(
        class_name=class_name,
        moras=(SvgGraphMora(text="ア", level=PitchLevel.low),),
        is_particle=is_particle,
        connect_to_previous=ConnectToPrevious.weld,
    )


class TestConnectorCssClass:
    """connector_css_class shares the accent class only for accented particles."""

    @pytest.mark.parametrize(
        "class_name, is_particle, expected_accented, expected_css_class",
        [
            (SvgGraphClassName.odaka, True, True, "connector particle odaka"),
            (SvgGraphClassName.atamadaka, True, True, "connector particle atamadaka"),
            (SvgGraphClassName.particle, True, False, "connector"),
            (SvgGraphClassName.atamadaka, False, False, "connector"),
            (SvgGraphClassName.heiban, False, False, "connector"),
        ],
    )
    def test_connector_css_class(
        self, class_name: SvgGraphClassName, is_particle: bool, expected_accented: bool, expected_css_class: str
    ) -> None:
        """Accented particles get a compound connector class; everything else stays neutral."""
        word = make_word(class_name, is_particle=is_particle)
        assert is_accented_particle(word) is expected_accented
        assert connector_css_class(word) == expected_css_class


def test_heiban_trailing_circle_has_fill_none(no_anki_config: NoAnkiConfigView) -> None:
    """Heiban dictionary graphs add a trailing hollow circle for following particles."""
    maker = FormattedEntryToSvgAdapter(no_anki_config)

    svg = maker.make_graph(TEST_ENTRIES[0])

    assert svg.count('<circle class="trail" fill="none" stroke="gray"') == 1


@pytest.mark.parametrize(
    "formatted_entry, expected_color, expected_color_pair_count",
    [
        (TEST_ENTRIES[0], "#005ce6", 4),
        (TEST_ENTRIES[1], "#ff6207", 6),
        (TEST_ENTRIES[5], "#e60000", 1),
    ],
)
def test_svg_attributes_color_mode(
    formatted_entry: FormattedEntry, expected_color: str, expected_color_pair_count: int
) -> None:
    """SVG attribute color mode writes role colors directly into SVG markup."""
    no_anki_config = make_fresh_config()
    no_anki_config.svg_graphs["color_mode"] = SvgGraphColorMode.svg_attributes.name

    svg = FormattedEntryToSvgAdapter(no_anki_config).make_graph(formatted_entry)

    assert svg.count(f'fill="{expected_color}" stroke="{expected_color}"') == expected_color_pair_count


@pytest.mark.parametrize("formatted_entry", TEST_ENTRIES)
def test_css_color_mode_omits_configured_colors(formatted_entry: FormattedEntry) -> None:
    """CSS color mode keeps role classes and a neutral fallback, not configured hex colors."""
    no_anki_config = make_fresh_config()
    no_anki_config.svg_graphs["color_mode"] = SvgGraphColorMode.css.name

    svg = FormattedEntryToSvgAdapter(no_anki_config).make_graph(formatted_entry)

    assert svg.count('class="ajt__pitch_svg"') == 1
    # In CSS mode the SVG relies on external CSS for coloring, so no configured hex colors are inlined.
    assert RE_HEX_COLOR.search(svg) is None


@pytest.mark.parametrize(
    "color_mode, expected_color",
    [
        (SvgGraphColorMode.black_and_white, SvgBlackAndWhiteRole.word.value),
        (SvgGraphColorMode.css, SvgBlackAndWhiteRole.word.value),
        (SvgGraphColorMode.svg_attributes, "#005ce6"),
    ],
)
def test_lookup_component_color_respects_color_mode(color_mode: SvgGraphColorMode, expected_color: str) -> None:
    """Color lookup uses configured colors only when SVG attributes mode is active."""
    no_anki_config = make_fresh_config()
    no_anki_config.svg_graphs["color_mode"] = color_mode.name

    assert lookup_component_color(no_anki_config, SvgBlackAndWhiteRole.word, SvgGraphClassName.heiban) == expected_color


def test_svg_graph_color_lookup_falls_back_to_black() -> None:
    """Missing SVG class color config falls back to the configured black color."""
    no_anki_config = make_fresh_config()
    del no_anki_config.svg_graph_colors.config[SvgGraphClassName.heiban.name]

    assert (
        no_anki_config.svg_graph_colors.lookup_color(SvgGraphClassName.heiban)
        == no_anki_config.svg_graph_colors[SvgGraphClassName.black]
    )


def test_color_mode_falls_back_to_svg_attributes() -> None:
    """Invalid color_mode config values fall back to SVG attributes mode."""
    no_anki_config = make_fresh_config()
    no_anki_config.svg_graphs["color_mode"] = "invalid_mode"

    assert no_anki_config.svg_graphs.color_mode == SvgGraphColorMode.svg_attributes


def test_svg_graph_class_names_have_config_colors_and_css_rules() -> None:
    """Every SVG graph class has a config color and a CSS selector."""
    class_names = frozenset(class_name.name for class_name in SvgGraphClassName)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    css_classes = frozenset(RE_CSS_CLASS_REFERENCE.findall(PITCH_GRAPH_CSS_PATH.read_text(encoding="utf-8")))

    assert frozenset(config["svg_graph_colors"]) == class_names
    assert class_names <= css_classes


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
    no_anki_config = make_fresh_config()
    no_anki_config.svg_graphs["include_text"] = include_text
    maker = FormattedEntryToSvgAdapter(no_anki_config)
    svg = maker.make_graph(formatted_entry)
    assert svg.count('<g class="text">') == expected_text_group_count


def test_renderer_uses_mutated_options() -> None:
    """Renderer geometry is computed from current options, not stale cached values."""
    no_anki_config = make_fresh_config()
    maker = FormattedEntryToSvgAdapter(no_anki_config)
    before = maker.make_graph(TEST_ENTRIES[0])
    no_anki_config.svg_graphs.update({
        "graph_horizontal_padding": 50,
        "size_unit": 40,
        "graph_height": 80,
    })

    after = maker.make_graph(TEST_ENTRIES[0])

    assert before != after
    # viewBox and the first circle appear once; the high-pitch y-coordinate appears once per high mora.
    assert [
        after.count(fragment) for fragment in ('viewBox="0 0 350 210"', 'cx="90.000" cy="120.000"', 'cy="40.000"')
    ] == [
        1,
        1,
        4,
    ]
