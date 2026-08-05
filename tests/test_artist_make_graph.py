# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Tests for SvgPitchArtistGraphMaker.make_graph(), verifying exact SVG output.

import re
import typing

import pytest

from japanese.helpers.misc import compact_seq
from japanese.pitch_accents.colors import SvgGraphClassName
from japanese.pitch_accents.svg_components import (
    SvgBlackAndWhiteRole,
    lookup_component_color,
)
from japanese.pitch_artist.pitch_graph import SvgPitchArtistGraphMaker
from playground.utils import NoAnkiConfigView
from tests.consts import DATA_DIR
from tests.helpers import (
    HEADLESS_SENTENCE,
    NUM_EXPECTED_SEQUENCES,
    CirclePosition,
    SvgRootDimensions,
    extract_circles,
    extract_group_class_names,
    extract_svg_root_dimensions,
    extract_text_labels,
    extract_visible_height,
    make_fresh_config,
    make_svg_attributes_config,
    render_first_graph,
)

# Circle Y-coordinates derived from default config:
#   height_high = size_unit = 25   → y=25 means "high"
#   height_low  = 25 + graph_height = 25 + 40 = 65  → y=65 means "low"
# Circle X-coordinates:
#   first = size_unit + graph_horizontal_padding = 25 + 6 = 31
#   step  = x_step = 50  →  31, 81, 131, 181, ...

HIGH: typing.Final = 25
LOW: typing.Final = 65

RE_EMPTY_GROUP: typing.Final = re.compile(r'<g(?: class="[^"]+")?></g>')
RE_PARTICLE_ATAMADAKA_CIRCLE_GROUP: typing.Final = re.compile(r'<g class="particle atamadaka"><circle[^>]+>')
RE_PARTICLE_CIRCLE_GROUP: typing.Final = re.compile(r'<g class="particle[^"]*"><circle[^>]+>')
RE_CIRCLE: typing.Final = re.compile(r"<circle[^>]+>")
RE_STROKE_DASHARRAY: typing.Final = re.compile(r'stroke-dasharray="')
RE_LINE: typing.Final = re.compile(r"<line")
RE_CONNECTOR_LINE_STROKE: typing.Final = re.compile(r'<g class="connector[^"]*"><line [^>]*stroke="(?P<stroke>[^"]+)"')


class ArtistGraphReference(typing.NamedTuple):
    """Expected Pitch Artist SVG graph reference file."""

    index: int
    svg_file_name: str


ARTIST_GRAPH_REFERENCES: typing.Final = tuple(
    ArtistGraphReference(index=index, svg_file_name=f"test_{index}.svg") for index in range(NUM_EXPECTED_SEQUENCES)
)


def make_artist_graphs(cfg: NoAnkiConfigView) -> list[str]:
    """Render the canonical Pitch Artist SVG snapshot set."""
    gen = SvgPitchArtistGraphMaker(cfg)
    return list(gen.make_graphs(gen.make_sequences(HEADLESS_SENTENCE)))


@pytest.mark.parametrize("reference", ARTIST_GRAPH_REFERENCES)
def test_make_artist_svg(no_anki_config: NoAnkiConfigView, reference: ArtistGraphReference) -> None:
    """Pitch Artist SVG output matches the checked-in full SVG references."""
    reference_file_path = DATA_DIR / "artist_graphs" / reference.svg_file_name
    expected_graph = reference_file_path.read_text(encoding="utf-8").strip()

    assert make_artist_graphs(no_anki_config)[reference.index].strip() == expected_graph


class TestCirclePositions:
    """Verify exact circle positions for each pitch pattern."""

    @pytest.mark.parametrize(
        "notation, expected_positions",
        [
            # heiban: low, low (ッ inherits low from j==1 rule), high, high
            (
                "がっこう;0",
                [
                    CirclePosition(31, LOW),
                    CirclePosition(81, LOW),
                    CirclePosition(131, HIGH),
                    CirclePosition(181, HIGH),
                ],
            ),
            # atamadaka: high, low, low, low
            (
                "がっこう;1",
                [
                    CirclePosition(31, HIGH),
                    CirclePosition(81, LOW),
                    CirclePosition(131, LOW),
                    CirclePosition(181, LOW),
                ],
            ),
            # nakadaka: low, high, low, low
            (
                "つくった;2",
                [
                    CirclePosition(31, LOW),
                    CirclePosition(81, HIGH),
                    CirclePosition(131, LOW),
                    CirclePosition(181, LOW),
                ],
            ),
            # odaka (3 moras, pitch 3): low, high, high
            (
                "ひとり;3",
                [
                    CirclePosition(31, LOW),
                    CirclePosition(81, HIGH),
                    CirclePosition(131, HIGH),
                ],
            ),
        ],
    )
    def test_circle_positions(
        self,
        no_anki_config: NoAnkiConfigView,
        notation: str,
        expected_positions: list[CirclePosition],
    ) -> None:
        """Circle centers land at the expected (x, y) positions for each pitch pattern."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        graphs = list(gen.make_graphs(sequences))
        assert len(graphs) == 1
        assert extract_circles(graphs[0]) == expected_positions


class TestSmallTsuSpecialCase:
    """ッ at j=1 inherits the low level from the previous mora."""

    def test_small_tsu_inherits_low(self, no_anki_config: NoAnkiConfigView) -> None:
        """ッ at j=1 inherits the low level from the previous mora."""
        # がっこう;0: moras are ガ, ッ, コ, ウ.
        # ッ is at j=1 and section.levels[0] is low → ッ inherits low.
        # Without this rule, ッ would be high (heiban pitch 0).
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]
        circles = extract_circles(svg)
        # Circle for ッ (index 1) must be low, not high.
        assert circles[1] == CirclePosition(81, LOW)


class TestTextLabels:
    """Verify the correct kana labels appear in <text> elements."""

    @pytest.mark.parametrize(
        "notation, expected_labels",
        [
            ("がっこう;0", ["ガ", "ッ", "コ", "ウ"]),
            ("がっこう;1", ["ガ", "ッ", "コ", "ウ"]),
            ("つくった;2", ["ツ", "ク", "ッ", "タ"]),
            ("ひとり;1", ["ヒ", "ト", "リ"]),
        ],
    )
    def test_text_labels(
        self,
        no_anki_config: NoAnkiConfigView,
        notation: str,
        expected_labels: list[str],
    ) -> None:
        """The correct kana labels appear in <text> elements."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        svg = list(gen.make_graphs(sequences))[0]
        assert extract_text_labels(svg) == expected_labels


class TestSvgGroupNames:
    """Root pitch-contour group keeps the shared 'lines' class name."""

    @pytest.mark.parametrize(
        "notation, expected_path_classes",
        [
            ("がっこう;0", ["lines"]),
            ("がっこう;1 つくった;2", ["lines"]),
            ("大物[おおもの];2 ; まで;1", ["lines"]),
        ],
    )
    def test_path_group_is_named_lines(
        self, no_anki_config: NoAnkiConfigView, notation: str, expected_path_classes: list[str]
    ) -> None:
        """The pitch-contour group keeps the shared 'lines' class name."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        svg = list(gen.make_graphs(gen.make_sequences(notation)))[0]
        group_class_names = extract_group_class_names(svg)

        assert group_class_names[:1] == expected_path_classes
        assert [class_name for class_name in group_class_names if class_name == "paths"] == []

    @pytest.mark.parametrize(
        "notation",
        [
            "きょう;1 は | てんき;1 が いい;1 です",
            "ひとり;1-",
            "君[dきdみ]; dの 嘘[dうdそ];1 dを.",
            "自分[じぶん]; じゃ | できない;k2.",
        ],
    )
    def test_no_empty_groups(self, no_anki_config: NoAnkiConfigView, notation: str) -> None:
        """Generated SVG omits all empty group elements."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        svg = list(gen.make_graphs(gen.make_sequences(notation)))[0]
        assert RE_EMPTY_GROUP.findall(svg) == []


class TestRoleClassNames:
    """Every renderable role resolves to its matching SVG class name."""

    @pytest.mark.parametrize(
        "notation, expected_class_name",
        [
            # Keihan roles.
            ("たべる;H;hh", "keihan_heiban"),
            ("たべる;L;hl", "keihan_low_heiban"),
            ("たべる;A;hl", "keihan_atamadaka"),
            ("たべる;N;hlh", "keihan_nakadaka"),
            ("たべる;M;hlh", "keihan_low_nakadaka"),
            ("たべる;O;hl", "keihan_low_odaka"),
            ("たべる;K;hlh", "keihan_kifuku"),
            # Special Tokyo roles.
            ("たべる;b", "black"),
            ("たべる;w", "white"),
            ("たべる;s", "setsubigo"),
        ],
    )
    def test_role_section_renders(
        self, no_anki_config: NoAnkiConfigView, notation: str, expected_class_name: str
    ) -> None:
        """Each role notation renders groups with the matching SVG class name."""
        svg = render_first_graph(no_anki_config, notation)
        group_class_names = extract_group_class_names(svg)
        # The section class appears in the lines, circles, and text groups; dedup to compare.
        assert compact_seq(name for name in group_class_names if name == expected_class_name) == (expected_class_name,)


class TestUnknownRoleClassNames:
    """Invalid role letters render with the unknown class instead of raising ValueError."""

    @pytest.mark.parametrize(
        "notation",
        [
            "テスト;z",
            "たべる;Z;hh",
            "たべる;Lo;hh",
            "テスト;zzzz;hh",
        ],
    )
    def test_invalid_role_renders_as_unknown(self, no_anki_config: NoAnkiConfigView, notation: str) -> None:
        """Each invalid role notation renders groups with the unknown class name."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        svg = list(gen.make_graphs(gen.make_sequences(notation)))[0]
        group_class_names = extract_group_class_names(svg)
        # The section class appears in the lines, circles, and text groups; dedup to compare.
        assert compact_seq(name for name in group_class_names if name == "unknown") == ("unknown",)


class TestGhostParticle:
    """Ghost particle (-) draws an empty circle but produces no text element."""

    def test_ghost_has_circle_but_no_text(self, no_anki_config: NoAnkiConfigView) -> None:
        """Ghost particle draws a trailing circle and line but no text element."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("ひとり;1-")
        svg = list(gen.make_graphs(sequences))[0]
        # 3 moras + 1 ghost = 4 circles.
        assert len(extract_circles(svg)) == 4
        # Ghost particle has no text.
        assert len(extract_text_labels(svg)) == 3
        # Ghost particle is visually equivalent to a trailing mora.
        assert svg.count('<circle class="trail" fill="none" stroke="gray"') == 1
        assert svg.count('<line class="trail" stroke="gray"') == 1


class TestParticleCircleFallback:
    """Particle circles use an inline fill="none" fallback when CSS is not injected."""

    def test_particle_circles_have_fill_none(self, no_anki_config: NoAnkiConfigView) -> None:
        """Particle circles are hollow (fill="none")."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("よねん; ぐらい;pa")
        svg = list(gen.make_graphs(sequences))[0]

        particle_circles = RE_PARTICLE_ATAMADAKA_CIRCLE_GROUP.findall(svg)
        assert particle_circles
        assert [circle.count('fill="none"') for circle in particle_circles] == [1]

    def test_normal_word_circles_remain_filled(self, no_anki_config: NoAnkiConfigView) -> None:
        """Non-particle circles stay filled."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]

        circles = RE_CIRCLE.findall(svg)
        assert circles
        assert [circle.count('fill="black"') for circle in circles] == [1, 1, 1, 1]


class TestParticleRoleColors:
    """Particles with an explicit pitch accent render in the accent's color; plain particles in the particle color."""

    @pytest.mark.parametrize(
        "notation, class_name",
        [
            # Particle with explicit atamadaka accent: circles use the atamadaka color.
            ("よねん; ぐらい;pa", SvgGraphClassName.atamadaka),
            # Plain particle without a pitch number: circles use the particle color.
            ("がっこう;0 は;p", SvgGraphClassName.particle),
        ],
    )
    def test_particle_circle_color_in_svg_attributes_mode(self, notation: str, class_name: SvgGraphClassName) -> None:
        """Circle stroke colors follow the section's role in SVG attributes mode."""
        cfg = make_svg_attributes_config()
        expected_stroke = lookup_component_color(cfg, SvgBlackAndWhiteRole.word, class_name)
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences(notation)))[0]

        particle_circles = RE_PARTICLE_CIRCLE_GROUP.findall(svg)
        assert particle_circles
        assert [circle.count(f'stroke="{expected_stroke}"') for circle in particle_circles] == [1] * len(
            particle_circles
        )

    def test_particle_connector_matches_accent_color(self) -> None:
        """The connector into an accented particle uses the accent's color, like the particle's circles."""
        cfg = make_svg_attributes_config()
        expected_stroke = lookup_component_color(cfg, SvgBlackAndWhiteRole.word, SvgGraphClassName.odaka)
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences("きょう;1 は;po")))[0]

        # The connector into は;po carries the section's compound class and the odaka color.
        assert svg.count(f'<g class="connector particle odaka"><line stroke="{expected_stroke}"') == 1
        # The particle circle is hollow and odaka-colored.
        assert svg.count(f'<g class="particle odaka"><circle fill="none" stroke="{expected_stroke}"') == 1


class TestNeutralConnectors:
    """Connectors into words or plain particles stay neutral gray in SVG attributes mode."""

    @pytest.mark.parametrize(
        "notation, expected_connector_count, expected_dashed_count",
        [
            # Connectors into で (particle), dくすり;0 (heiban word), を (particle), のんだ;1 (atamadaka word).
            ("dひとり;2 で dくすり;0 を のんだ;1", 4, 0),
            # Break (|) before てんき;1: no connector at all. Other connectors stay gray.
            ("きょう;1 は;p | てんき;1 が いい;1 です", 4, 0),
            # Break (|) before てんき;1: no connector. Tape (;) before いい;1: dashed gray connector.
            ("きょう;1 は | てんき;1 が ; いい;1 です", 4, 1),
        ],
    )
    def test_connectors_into_words_stay_gray(
        self, notation: str, expected_connector_count: int, expected_dashed_count: int
    ) -> None:
        """Connectors into words and plain particles keep the neutral connector color."""
        cfg = make_svg_attributes_config()
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences(notation)))[0]

        # Every connector group keeps the neutral class and the gray connector color.
        assert [name for name in extract_group_class_names(svg) if name.startswith("connector")] == [
            "connector"
        ] * expected_connector_count
        assert RE_CONNECTOR_LINE_STROKE.findall(svg) == ["gray"] * expected_connector_count
        # Tape connectors are dashed but equally neutral.
        assert svg.count('<line stroke-dasharray="4" stroke="gray"') == expected_dashed_count


class TestDevoicedMora:
    """Devoiced mora text elements have class='devoiced' and get devoiced circle markers."""

    def test_devoiced_has_class_and_circle(self, no_anki_config: NoAnkiConfigView) -> None:
        """Devoiced mora text gets class="devoiced" and dashed circle markers."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("君[dきdみ];1")
        svg = list(gen.make_graphs(sequences))[0]
        # Devoiced text elements have class="devoiced".
        assert svg.count('class="devoiced"') >= 2
        # Devoiced circle markers use stroke-dasharray (dashed circles/rects).
        dasharray_count = len(RE_STROKE_DASHARRAY.findall(svg))
        assert dasharray_count >= 2  # one for each devoiced mora (き and み)


class TestTapeConnector:
    """Tape connector lines have stroke-dasharray='4'."""

    def test_tape_has_dasharray(self, no_anki_config: NoAnkiConfigView) -> None:
        """Tape connector lines use stroke-dasharray."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("大物[おおもの];2 ; まで;1")
        svg = list(gen.make_graphs(sequences))[0]
        # Tape connector line should use stroke-dasharray="4".
        assert svg.count('stroke-dasharray="4"') == 1

    @pytest.mark.parametrize(
        "notation, expected_circles, expected_texts",
        [
            # A leading tape has no rendered mora before it, so it must not create a connector from nowhere.
            ("; -", 1, 0),
            ("; せいかつ;", 4, 4),
            ("| ; せいかつ;", 4, 4),
        ],
    )
    def test_leading_tape_has_no_connector(
        self, no_anki_config: NoAnkiConfigView, notation: str, expected_circles: int, expected_texts: int
    ) -> None:
        """A leading tape creates no connector from nowhere."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        svg = list(gen.make_graphs(sequences))[0]

        assert len(extract_circles(svg)) == expected_circles
        assert len(extract_text_labels(svg)) == expected_texts
        # Connector groups carry the incoming section's class, e.g. "connector particle".
        assert [class_name for class_name in extract_group_class_names(svg) if class_name.startswith("connector")] == []
        assert svg.count('stroke-dasharray="4"') == 0


class TestIncludeText:
    """When include_text is False, no <text> elements appear and height shrinks."""

    @pytest.mark.parametrize(
        "include_text, expected_dimensions, expected_text_count",
        [
            (True, SvgRootDimensions(view_box_width=212, view_box_height=140, visible_height=100), 4),
            (False, SvgRootDimensions(view_box_width=212, view_box_height=90, visible_height=64), 0),
        ],
    )
    def test_svg_dimensions_are_integer_formatted(
        self, include_text: bool, expected_dimensions: SvgRootDimensions, expected_text_count: int
    ) -> None:
        """Root SVG dimensions remain integer-formatted when kana text is toggled."""
        cfg = make_fresh_config()
        cfg.svg_graphs["include_text"] = include_text
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences("がっこう;0")))[0]

        assert extract_svg_root_dimensions(svg) == expected_dimensions
        assert len(extract_text_labels(svg)) == expected_text_count

    def test_no_text_when_disabled(self) -> None:
        """include_text=False omits text elements and shrinks the visible height."""
        cfg = make_fresh_config()
        cfg.svg_graphs["include_text"] = False
        gen = SvgPitchArtistGraphMaker(cfg)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]
        # No text elements.
        assert len(extract_text_labels(svg)) == 0
        # Circles and lines still present.
        assert len(extract_circles(svg)) == 4
        assert len(RE_LINE.findall(svg)) == 3
        # Visible height shrinks (64 instead of 100).
        assert extract_visible_height(svg) == 64

    def test_text_present_when_enabled(self, no_anki_config: NoAnkiConfigView) -> None:
        """include_text=True renders text labels at full height."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]
        assert len(extract_text_labels(svg)) == 4
        assert extract_visible_height(svg) == 100

    @pytest.mark.parametrize(
        "include_text, expected_text_group_count",
        [
            (False, 0),
            (True, 1),
        ],
    )
    def test_text_group_matches_text_visibility(self, include_text: bool, expected_text_group_count: int) -> None:
        """Text group markup is emitted only when kana text is visible."""
        cfg = make_fresh_config()
        cfg.svg_graphs["include_text"] = include_text
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences("がっこう;0")))[0]
        assert svg.count('<g class="text">') == expected_text_group_count


class TestEmptyInput:
    """Edge cases where make_graph returns None."""

    def test_empty_sequence_returns_none(self, no_anki_config: NoAnkiConfigView) -> None:
        """An empty sequence produces no graph (None)."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        assert gen.make_graph([]) is None

    def test_pipe_only_produces_no_graphs(self, no_anki_config: NoAnkiConfigView) -> None:
        """A pipe-only input produces no graphs."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("|")
        graphs = list(gen.make_graphs(sequences))
        assert len(graphs) == 0


class TestMultiWordConnector:
    """Connected words have a connector line group between them."""

    def test_connector_present(self, no_anki_config: NoAnkiConfigView) -> None:
        """Connected words have a connector group between them."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;1 つくった;2")
        svg = list(gen.make_graphs(sequences))[0]
        # A connector group should exist, keeping the neutral class (つくった;2 is a word, not an accented particle).
        assert [class_name for class_name in extract_group_class_names(svg) if class_name.startswith("connector")] == [
            "connector"
        ]

    def test_disconnected_words_have_no_connector(self, no_anki_config: NoAnkiConfigView) -> None:
        """Pipe-disconnected words have no connector group."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;1 | つくった;2")
        svg = list(gen.make_graphs(sequences))[0]
        # Pipe disconnects → no connector group.
        assert [class_name for class_name in extract_group_class_names(svg) if class_name.startswith("connector")] == []
