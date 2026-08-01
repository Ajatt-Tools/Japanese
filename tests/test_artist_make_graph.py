# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Tests for SvgPitchArtistGraphMaker.make_graph(), verifying exact SVG output.

import re
import typing

import pytest

from japanese.pitch_artist.pitch_graph import SvgPitchArtistGraphMaker
from playground.utils import NoAnkiConfigView
from tests.consts import DATA_DIR
from tests.test_pitch_artist_regression import HEADLESS_SENTENCE, NUM_EXPECTED_SEQUENCES

# Circle Y-coordinates derived from default config:
#   height_high = size_unit = 25   → y=25 means "high"
#   height_low  = 25 + graph_height = 25 + 40 = 65  → y=65 means "low"
# Circle X-coordinates:
#   first = size_unit + graph_horizontal_padding = 25 + 6 = 31
#   step  = x_step = 50  →  31, 81, 131, 181, ...

HIGH = 25
LOW = 65


class SvgRootDimensions(typing.NamedTuple):
    """Integer dimensions declared on the root SVG element."""

    view_box_width: int
    view_box_height: int
    visible_height: int


class ArtistGraphReference(typing.NamedTuple):
    """Expected Pitch Artist SVG graph reference file."""

    index: int
    svg_file_name: str


ARTIST_GRAPH_REFERENCES = tuple(
    ArtistGraphReference(index=index, svg_file_name=f"test_{index}.svg") for index in range(NUM_EXPECTED_SEQUENCES)
)


class CirclePosition(typing.NamedTuple):
    """Integer circle center coordinates in SVG user units."""

    x: int
    y: int


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


def extract_circles(svg: str) -> list[CirclePosition]:
    """Extract (x, y) integer pairs from all <circle> elements in the SVG."""
    return [
        CirclePosition(x=int(float(match.group("cx"))), y=int(float(match.group("cy"))))
        for match in re.finditer(r'cx="(?P<cx>[0-9.]+)" cy="(?P<cy>[0-9.]+)"', svg)
    ]


def extract_text_labels(svg: str) -> list[str]:
    """Extract text content from all <text> elements in the SVG."""
    return [match.group("label") for match in re.finditer(r"<text[^>]*>(?P<label>[^<]*)</text>", svg)]


def extract_group_class_names(svg: str) -> list[str]:
    """Extract CSS class names from all SVG group elements."""
    return re.findall(r'<g class="(?P<class_name>[^"]+)">', svg)


def extract_svg_root_dimensions(svg: str) -> SvgRootDimensions:
    """Extract integer root SVG dimensions from viewBox and height attributes."""
    match = re.search(
        r'viewBox="0 0 (?P<view_box_width>\d+) (?P<view_box_height>\d+)" height="(?P<visible_height>\d+)px"',
        svg,
    )
    assert match is not None, "integer root SVG dimensions not found"
    return SvgRootDimensions(
        view_box_width=int(match.group("view_box_width")),
        view_box_height=int(match.group("view_box_height")),
        visible_height=int(match.group("visible_height")),
    )


def extract_visible_height(svg: str) -> int:
    """Extract the visible height (in pixels) from the SVG root element."""
    return extract_svg_root_dimensions(svg).visible_height


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
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        graphs = list(gen.make_graphs(sequences))
        assert len(graphs) == 1
        assert extract_circles(graphs[0]) == expected_positions


class TestSmallTsuSpecialCase:
    """ッ at j=1 inherits the low level from the previous mora."""

    def test_small_tsu_inherits_low(self, no_anki_config: NoAnkiConfigView) -> None:
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
        assert re.findall(r'<g(?: class="[^"]+")?></g>', svg) == []


class TestGhostParticle:
    """Ghost particle (-) draws an empty circle but produces no text element."""

    def test_ghost_has_circle_but_no_text(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("ひとり;1-")
        svg = list(gen.make_graphs(sequences))[0]
        # 3 moras + 1 ghost = 4 circles.
        assert len(extract_circles(svg)) == 4
        # Ghost particle has no text.
        assert len(extract_text_labels(svg)) == 3


class TestParticleCircleFallback:
    """Particle circles use an inline fill="none" fallback when CSS is not injected."""

    def test_particle_circles_have_fill_none(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("よねん; ぐらい;pa")
        svg = list(gen.make_graphs(sequences))[0]

        particle_circles = re.findall(r'<g class="particle atamadaka"><circle[^>]+>', svg)
        assert particle_circles
        assert [circle.count('fill="none"') for circle in particle_circles] == [1]

    def test_normal_word_circles_remain_filled(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]

        circles = re.findall(r"<circle[^>]+>", svg)
        assert circles
        assert [circle.count('fill="black"') for circle in circles] == [1, 1, 1, 1]


class TestDevoicedMora:
    """Devoiced mora text elements have class='devoiced' and get devoiced circle markers."""

    def test_devoiced_has_class_and_circle(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("君[dきdみ];1")
        svg = list(gen.make_graphs(sequences))[0]
        # Devoiced text elements have class="devoiced".
        assert svg.count('class="devoiced"') >= 2
        # Devoiced circle markers use stroke-dasharray (dashed circles/rects).
        dasharray_count = len(re.findall(r'stroke-dasharray="', svg))
        assert dasharray_count >= 2  # one for each devoiced mora (き and み)


class TestTapeConnector:
    """Tape connector lines have stroke-dasharray='4'."""

    def test_tape_has_dasharray(self, no_anki_config: NoAnkiConfigView) -> None:
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
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        svg = list(gen.make_graphs(sequences))[0]

        assert len(extract_circles(svg)) == expected_circles
        assert len(extract_text_labels(svg)) == expected_texts
        assert [class_name for class_name in extract_group_class_names(svg) if class_name == "connector"] == []
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
        cfg = NoAnkiConfigView()
        cfg.svg_graphs["include_text"] = include_text
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences("がっこう;0")))[0]

        assert extract_svg_root_dimensions(svg) == expected_dimensions
        assert len(extract_text_labels(svg)) == expected_text_count

    def test_no_text_when_disabled(self) -> None:
        # Create a fresh config to avoid mutating the shared session fixture.
        cfg = NoAnkiConfigView()
        cfg.svg_graphs["include_text"] = False
        gen = SvgPitchArtistGraphMaker(cfg)
        sequences = gen.make_sequences("がっこう;0")
        svg = list(gen.make_graphs(sequences))[0]
        # No text elements.
        assert len(extract_text_labels(svg)) == 0
        # Circles and lines still present.
        assert len(extract_circles(svg)) == 4
        assert len(re.findall(r"<line", svg)) == 3
        # Visible height shrinks (64 instead of 100).
        assert extract_visible_height(svg) == 64

    def test_text_present_when_enabled(self, no_anki_config: NoAnkiConfigView) -> None:
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
        cfg = NoAnkiConfigView()
        cfg.svg_graphs["include_text"] = include_text
        gen = SvgPitchArtistGraphMaker(cfg)
        svg = list(gen.make_graphs(gen.make_sequences("がっこう;0")))[0]
        assert svg.count('<g class="text">') == expected_text_group_count


class TestEmptyInput:
    """Edge cases where make_graph returns None."""

    def test_empty_sequence_returns_none(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        assert gen.make_graph([]) is None

    def test_pipe_only_produces_no_graphs(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("|")
        graphs = list(gen.make_graphs(sequences))
        assert len(graphs) == 0


class TestMultiWordConnector:
    """Connected words have a connector line group between them."""

    def test_connector_present(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;1 つくった;2")
        svg = list(gen.make_graphs(sequences))[0]
        # A "connector" CSS class group should exist.
        assert [class_name for class_name in extract_group_class_names(svg) if class_name == "connector"] == [
            "connector"
        ]

    def test_disconnected_words_have_no_connector(self, no_anki_config: NoAnkiConfigView) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences("がっこう;1 | つくった;2")
        svg = list(gen.make_graphs(sequences))[0]
        # Pipe disconnects → no connector group.
        assert [class_name for class_name in extract_group_class_names(svg) if class_name == "connector"] == []
