# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Regression tests for Pitch Artist, using reference data

import re
import typing

import pytest

from japanese.pitch_artist.consts import GHOST_PARTICLE, TAPE_CONNECTOR
from japanese.pitch_artist.pitch_graph import (
    Role,
    SvgPitchArtistGraphMaker,
    adjust_ha_wa,
    apply_kanji_colors,
    guess_role_from_pitch_num,
    is_empty_section,
    make_section,
)
from japanese.pitch_artist.split import ArtistMora, SplitAccent, split_accent
from playground.utils import NoAnkiConfigView

# The canonical test sentences.
HEADLESS_SENTENCE = """
大物[おおもの];2 ; まで;1
じんせい;1 | まで;1
じんせい;1 ; まで;a-1
つかう; , つかった;-
稼[かせ]いで;k2. がっこう;
がっこう;1. つくった;2.
君[dきdみ]; dの 嘘[dうdそ];1 dを.
自分[じぶん]; じゃ | できない;k2.
ひとり;1-
ひとり;2-
ひとり;3-
よねん; ぐらい;pa
よねん; ぐらい;po1
"""

NUM_EXPECTED_SEQUENCES = 15


class ExpectedSection(typing.NamedTuple):
    """Expected section-level data for regression testing."""

    word: str
    role_name: str
    pitch: int
    is_particle: bool
    mora_count: int
    level_names: list[str]


class ExpectedSvgStructure(typing.NamedTuple):
    """Expected SVG element counts and CSS classes for regression testing."""

    num_circles: int
    num_lines: int
    num_texts: int
    css_classes: list[str]


# Section-level reference data.
EXPECTED_SEQUENCES: list[list[ExpectedSection]] = [
    # seq 0: 大物[おおもの];2 ; まで;1
    [
        ExpectedSection("大物[おおもの]", "nakadaka", 2, False, 4, ["low", "high", "low", "low"]),
        ExpectedSection(";", "empty", -1, False, 0, []),
        ExpectedSection("まで", "atamadaka", 1, False, 2, ["high", "low"]),
    ],
    # seq 1: じんせい;1 | まで;1
    [
        ExpectedSection("じんせい", "atamadaka", 1, False, 4, ["high", "low", "low", "low"]),
        ExpectedSection("|", "empty", -1, False, 0, []),
        ExpectedSection("まで", "atamadaka", 1, False, 2, ["high", "low"]),
    ],
    # seq 2: じんせい;1 ; まで;a-1
    [
        ExpectedSection("じんせい", "atamadaka", 1, False, 4, ["high", "low", "low", "low"]),
        ExpectedSection(";", "empty", -1, False, 0, []),
        ExpectedSection("まで", "atamadaka", -1, False, 2, ["low", "low"]),
    ],
    # seq 3: つかう; , つかった;-
    [
        ExpectedSection("つかう", "heiban", 0, False, 3, ["low", "high", "high"]),
        ExpectedSection(",", "empty", -1, False, 0, []),
        ExpectedSection("つかった", "heiban", 0, False, 4, ["low", "high", "high", "high"]),
        ExpectedSection("-", "particle", -2, True, 1, ["high"]),
    ],
    # seq 4: 稼[かせ]いで;k2
    [ExpectedSection("稼[かせ]いで", "kifuku", 2, False, 4, ["low", "high", "low", "low"])],
    # seq 5: がっこう;
    [ExpectedSection("がっこう", "heiban", 0, False, 4, ["low", "high", "high", "high"])],
    # seq 6: がっこう;1
    [ExpectedSection("がっこう", "atamadaka", 1, False, 4, ["high", "low", "low", "low"])],
    # seq 7: つくった;2
    [ExpectedSection("つくった", "nakadaka", 2, False, 4, ["low", "high", "low", "low"])],
    # seq 8: 君[dきdみ]; dの 嘘[dうdそ];1 dを.
    [
        ExpectedSection("君[きみ]", "heiban", 0, False, 2, ["low", "high"]),
        ExpectedSection("の", "particle", -2, True, 1, ["high"]),
        ExpectedSection("嘘[うそ]", "atamadaka", 1, False, 2, ["high", "low"]),
        ExpectedSection("を", "particle", -1, True, 1, ["low"]),
    ],
    # seq 9: 自分[じぶん]; じゃ | できない;k2.
    [
        ExpectedSection("自分[じぶん]", "heiban", 0, False, 3, ["low", "high", "high"]),
        ExpectedSection("じゃ", "particle", -2, True, 1, ["high"]),
        ExpectedSection("|", "empty", -1, False, 0, []),
        ExpectedSection("できない", "kifuku", 2, False, 4, ["low", "high", "low", "low"]),
    ],
    # seq 10: ひとり;1-
    [
        ExpectedSection("ひとり", "atamadaka", 1, False, 3, ["high", "low", "low"]),
        ExpectedSection("-", "particle", -1, True, 1, ["low"]),
    ],
    # seq 11: ひとり;2-
    [
        ExpectedSection("ひとり", "nakadaka", 2, False, 3, ["low", "high", "low"]),
        ExpectedSection("-", "particle", -1, True, 1, ["low"]),
    ],
    # seq 12: ひとり;3-
    [
        ExpectedSection("ひとり", "odaka", 3, False, 3, ["low", "high", "high"]),
        ExpectedSection("-", "particle", -1, True, 1, ["low"]),
    ],
    # seq 13: よねん; ぐらい;pa
    [
        ExpectedSection("よねん", "heiban", 0, False, 3, ["low", "high", "high"]),
        ExpectedSection("ぐらい", "atamadaka", 1, True, 3, ["high", "low", "low"]),
    ],
    # seq 14: よねん; ぐらい;po1
    [
        ExpectedSection("よねん", "heiban", 0, False, 3, ["low", "high", "high"]),
        ExpectedSection("ぐらい", "odaka", 1, True, 3, ["high", "low", "low"]),
    ],
]

# Reference SVG structural properties.
EXPECTED_SVG_STRUCTURE: list[ExpectedSvgStructure] = [
    ExpectedSvgStructure(
        6,
        5,
        6,
        [
            "lines",
            "nakadaka",
            "atamadaka",
            "connector",
            "circles",
            "nakadaka",
            "atamadaka",
            "text",
            "nakadaka",
            "atamadaka",
        ],
    ),
    ExpectedSvgStructure(
        6,
        4,
        6,
        ["lines", "atamadaka", "atamadaka", "circles", "atamadaka", "atamadaka", "text", "atamadaka", "atamadaka"],
    ),
    ExpectedSvgStructure(
        6,
        5,
        6,
        [
            "lines",
            "atamadaka",
            "atamadaka",
            "connector",
            "circles",
            "atamadaka",
            "atamadaka",
            "text",
            "atamadaka",
            "atamadaka",
        ],
    ),
    ExpectedSvgStructure(
        8,
        6,
        7,
        [
            "lines",
            "heiban",
            "heiban",
            "particle",
            "connector",
            "circles",
            "heiban",
            "heiban",
            "particle",
            "text",
            "heiban",
            "heiban",
            "particle",
        ],
    ),
    ExpectedSvgStructure(4, 3, 4, ["lines", "kifuku", "circles", "kifuku", "text", "kifuku"]),
    ExpectedSvgStructure(4, 3, 4, ["lines", "heiban", "circles", "heiban", "text", "heiban"]),
    ExpectedSvgStructure(4, 3, 4, ["lines", "atamadaka", "circles", "atamadaka", "text", "atamadaka"]),
    ExpectedSvgStructure(4, 3, 4, ["lines", "nakadaka", "circles", "nakadaka", "text", "nakadaka"]),
    ExpectedSvgStructure(
        12,
        5,
        6,
        [
            "lines",
            "heiban",
            "particle",
            "connector",
            "atamadaka",
            "connector",
            "particle",
            "connector",
            "circles",
            "heiban",
            "particle",
            "atamadaka",
            "particle",
            "text",
            "heiban",
            "particle",
            "atamadaka",
            "particle",
        ],
    ),
    ExpectedSvgStructure(
        8,
        6,
        8,
        [
            "lines",
            "heiban",
            "particle",
            "connector",
            "kifuku",
            "circles",
            "heiban",
            "particle",
            "kifuku",
            "text",
            "heiban",
            "particle",
            "kifuku",
        ],
    ),
    ExpectedSvgStructure(
        4,
        3,
        3,
        [
            "lines",
            "atamadaka",
            "particle",
            "connector",
            "circles",
            "atamadaka",
            "particle",
            "text",
            "atamadaka",
            "particle",
        ],
    ),
    ExpectedSvgStructure(
        4,
        3,
        3,
        [
            "lines",
            "nakadaka",
            "particle",
            "connector",
            "circles",
            "nakadaka",
            "particle",
            "text",
            "nakadaka",
            "particle",
        ],
    ),
    ExpectedSvgStructure(
        4,
        3,
        3,
        ["lines", "odaka", "particle", "connector", "circles", "odaka", "particle", "text", "odaka", "particle"],
    ),
    ExpectedSvgStructure(
        6,
        5,
        6,
        [
            "lines",
            "heiban",
            "particle atamadaka",
            "connector",
            "circles",
            "heiban",
            "particle atamadaka",
            "text",
            "heiban",
            "particle atamadaka",
        ],
    ),
    ExpectedSvgStructure(
        6,
        5,
        6,
        [
            "lines",
            "heiban",
            "particle odaka",
            "connector",
            "circles",
            "heiban",
            "particle odaka",
            "text",
            "heiban",
            "particle odaka",
        ],
    ),
]


# ======================================================================
# Pure function tests
# ======================================================================


class TestSplitAccentExpanded:
    """Expanded tests for split_accent covering all dialect modes."""

    @pytest.mark.parametrize(
        "expression, expected",
        [
            # Keihan dialect
            ("h;hl", SplitAccent(is_particle=None, role="h", pitch=None, levels="hl", keihan=True)),
            # Tokyo: particle + role
            ("pa", SplitAccent(is_particle="p", role="a", pitch=None, keihan=False, levels=None)),
            # Tokyo: particle + role + pitch
            ("po1", SplitAccent(is_particle="p", role="o", pitch="1", keihan=False, levels=None)),
            # Tokyo: particle only (p = pp in role)
            ("p", SplitAccent(is_particle="p", role="p", pitch=None, keihan=False, levels=None)),
            # Tokyo: role only
            ("h", SplitAccent(is_particle=None, role="h", pitch=None, keihan=False, levels=None)),
            ("a", SplitAccent(is_particle=None, role="a", pitch=None, keihan=False, levels=None)),
            # Tokyo: role + pitch
            ("k3", SplitAccent(is_particle=None, role="k", pitch="3", keihan=False, levels=None)),
            # Tokyo: pitch only
            ("0", SplitAccent(is_particle=None, role=None, pitch="0", keihan=False, levels=None)),
            ("1", SplitAccent(is_particle=None, role=None, pitch="1", keihan=False, levels=None)),
            # Empty
            ("", SplitAccent(is_particle=None, role=None, pitch=None, keihan=False, levels=None)),
        ],
    )
    def test_split_accent(self, expression: str, expected: SplitAccent) -> None:
        assert split_accent(expression) == expected


class TestIsEmptySection:
    @pytest.mark.parametrize(
        "word, expected",
        [
            (TAPE_CONNECTOR, True),
            ("|", True),
            (",", True),
            ("、", True),
            (GHOST_PARTICLE, False),
            ("は", False),
            ("a", False),
            ("", True),
        ],
    )
    def test_is_empty_section(self, word: str, expected: bool) -> None:
        assert is_empty_section(word) is expected


class TestGuessRoleFromPitchNum:
    @pytest.mark.parametrize(
        "moras, pitch_n, expected",
        [
            (["ヒ", "ト", "リ"], "0", Role.heiban),
            (["ヒ", "ト", "リ"], "1", Role.atamadaka),
            (["ヒ", "ト", "リ"], "2", Role.nakadaka),
            (["ヒ", "ト", "リ"], "3", Role.odaka),
            (["ヒ", "ト", "リ"], None, Role.heiban),
            (["ヒ", "ト", "リ"], "-1", Role.particle),
        ],
    )
    def test_guess_role(self, moras: list[str], pitch_n: str | None, expected: Role) -> None:
        assert guess_role_from_pitch_num(len(moras), pitch_n) == expected


class TestAdjustHaWa:
    @pytest.mark.parametrize(
        "moras, expected",
        [
            (["ハ"], ["ワ"]),
            (["は"], ["わ"]),
            (["ヒ", "ト", "リ"], ["ヒ", "ト", "リ"]),
            (["カ"], ["カ"]),
        ],
    )
    def test_adjust_ha_wa(self, moras: list[str], expected: list[str]) -> None:
        assert adjust_ha_wa([ArtistMora.from_text(m) for m in moras]) == [ArtistMora.from_text(m) for m in expected]


class TestClassName:
    """Test the Section.class_name property through make_section."""

    @pytest.mark.parametrize(
        "raw_section, expected",
        [
            ("テスト;0", "heiban"),
            ("テスト;1", "atamadaka"),
            # is_particle=True with non-particle role produces two CSS classes.
            ("ぐらい;pa", "particle atamadaka"),
            ("ぐらい;po1", "particle odaka"),
            # is_particle=True with particle role does not duplicate.
            ("ぐらい;p", "particle"),
            # Bare particle (no p prefix, role defaults to particle).
            ("テスト", "particle"),
        ],
    )
    def test_class_name(
        self,
        no_anki_config: NoAnkiConfigView,
        raw_section: str,
        expected: str,
    ) -> None:
        section = make_section(raw_section, no_anki_config)
        assert section.class_name == expected


class TestNumericsExcludesBooleans:
    """Verify that numerics() does not return boolean config keys.

    bool is a subclass of int in Python, so a naive isinstance(value, (int, float))
    check would incorrectly include booleans. This test guards against that regression.
    """

    def test_bool_keys_not_in_numerics(self, no_anki_config: NoAnkiConfigView) -> None:
        numeric_keys = {item.cfg_key for item in no_anki_config.svg_graphs.numerics()}
        bool_keys = set(no_anki_config.svg_graphs.bool_keys())
        assert numeric_keys.isdisjoint(bool_keys), f"Boolean keys found in numerics: {numeric_keys & bool_keys}"


# ======================================================================
# Integration tests
# ======================================================================


class TestMakeSectionExpanded:
    """Test make_section with known inputs, verifying all parsed fields."""

    @pytest.mark.parametrize(
        "raw_section, expected_word, expected_role, expected_pitch, expected_is_particle, expected_mora_count",
        [
            ("ひとり;1", "ひとり", Role.atamadaka, 1, False, 3),
            ("ぐらい;pa", "ぐらい", Role.atamadaka, 1, True, 3),
            ("ぐらい;po1", "ぐらい", Role.odaka, 1, True, 3),
            ("がっこう;", "がっこう", Role.heiban, 0, False, 4),
            ("大物[おおもの];2", "大物[おおもの]", Role.nakadaka, 2, False, 4),
            ("がっこう;1", "がっこう", Role.atamadaka, 1, False, 4),
            ("つくった;2", "つくった", Role.nakadaka, 2, False, 4),
            ("稼[かせ]いで;k2", "稼[かせ]いで", Role.kifuku, 2, False, 4),
        ],
    )
    def test_make_section(
        self,
        no_anki_config: NoAnkiConfigView,
        raw_section: str,
        expected_word: str,
        expected_role: Role,
        expected_pitch: int,
        expected_is_particle: bool,
        expected_mora_count: int,
    ) -> None:
        section = make_section(raw_section, no_anki_config)
        assert section.word == expected_word
        assert section.role == expected_role
        assert section.pitch == expected_pitch
        assert section.is_particle == expected_is_particle
        assert len(section.moras) == expected_mora_count


# ======================================================================
# Headless.py canonical examples — regression tests
# ======================================================================


class TestHeadlessExamples:
    """Regression tests using reference test sentences."""

    @pytest.mark.parametrize("index", list(range(NUM_EXPECTED_SEQUENCES)))
    def test_section_data(self, no_anki_config: NoAnkiConfigView, index: int) -> None:
        """Compare section-level data against reference output."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(HEADLESS_SENTENCE)
        assert len(sequences) == NUM_EXPECTED_SEQUENCES
        seq = sequences[index]
        expected = EXPECTED_SEQUENCES[index]
        assert len(seq) == len(expected), f"section count mismatch in sequence {index}"
        for actual, exp in zip(seq, expected):
            assert actual.word == exp.word, f"word mismatch in seq {index}"
            assert actual.role.name == exp.role_name, f"role mismatch in seq {index}"
            assert actual.pitch == exp.pitch, f"pitch mismatch in seq {index}"
            assert actual.is_particle == exp.is_particle, f"is_particle mismatch in seq {index}"
            assert len(actual.moras) == exp.mora_count, f"mora count mismatch in seq {index}"
            if exp.level_names:
                actual_levels = [level.name for level in actual.levels]
                assert actual_levels == exp.level_names, f"levels mismatch in seq {index}"


class TestSvgRegression:
    """Compare SVG structural properties against pre-generated reference data."""

    @pytest.mark.parametrize("index", list(range(NUM_EXPECTED_SEQUENCES)))
    def test_svg_structure(self, no_anki_config: NoAnkiConfigView, index: int) -> None:
        """Compare circle/line/text counts and CSS classes against the reference."""
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(HEADLESS_SENTENCE)
        assert len(sequences) == NUM_EXPECTED_SEQUENCES
        graphs = list(gen.make_graphs(sequences))
        svg = graphs[index]

        expected = EXPECTED_SVG_STRUCTURE[index]

        assert len(re.findall(r"<circle", svg)) == expected.num_circles
        assert len(re.findall(r"<line", svg)) == expected.num_lines
        assert len(re.findall(r"<text", svg)) == expected.num_texts
        assert re.findall(r'<g class="([^"]+)"', svg) == expected.css_classes


class TestApplyKanjiColors:
    """Test apply_kanji_colors generates correct HTML spans with role-based CSS classes."""

    @pytest.mark.parametrize(
        "notation, expected",
        [
            ("ねこ;1", ['<span class="atamadaka">ねこ</span>']),
            ("がっこう;0 まで;1", ['<span class="heiban">がっこう</span><span class="atamadaka">まで</span>']),
            (
                "がっこう;1. つくった;2.",
                ['<span class="atamadaka">がっこう</span>', '<span class="nakadaka">つくった</span>'],
            ),
            (
                "がっこう;1 | つくった;2",
                ['<span class="atamadaka">がっこう</span><span class="nakadaka">つくった</span>'],
            ),
        ],
    )
    def test_apply_kanji_colors(
        self,
        no_anki_config: NoAnkiConfigView,
        notation: str,
        expected: list[str],
    ) -> None:
        gen = SvgPitchArtistGraphMaker(no_anki_config)
        sequences = gen.make_sequences(notation)
        assert apply_kanji_colors(sequences) == expected
