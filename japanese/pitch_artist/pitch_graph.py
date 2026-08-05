# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import enum
from collections.abc import Iterable, Sequence
from enum import Enum

from ..config_view import JapaneseConfig, SvgGraphReadingFormat
from ..mecab_controller import to_hiragana, to_katakana
from ..pitch_accents.colors import SvgGraphClassName
from ..pitch_accents.svg_graph_renderer import SvgGraphRenderer
from ..pitch_accents.svg_graph_types import (
    ConnectToPrevious,
    PitchLevel,
    SvgGraph,
    SvgGraphMora,
    SvgGraphWord,
    SvgMoraFlag,
)
from .consts import (
    DEVOICED_PREFIX,
    NON_RENDERED_SECTIONS,
    PITCH_BREAKS,
    SMALL_TSU,
    TAPE_CONNECTOR,
    TEXT_HIDDEN,
)
from .split import (
    ArtistMora,
    SectionParts,
    SplitAccent,
    detach_ghost_particle,
    furigana_to_reading,
    normalize_for_parsing,
    split_accent,
    split_multiple_pitch_notations,
    split_section,
    split_to_moras,
    split_to_sections,
    split_to_sentences,
)


@enum.unique
class Role(Enum):
    """Pitch accent pattern roles for Tokyo and Keihan dialects."""

    heiban = "h"
    atamadaka = "a"
    nakadaka = "n"
    odaka = "o"
    kifuku = "k"

    black = "b"
    white = "w"
    setsubigo = "s"
    empty = "e"
    particle = "p"
    # Invalid role letters (e.g. ";z", ";Lo;hh") fall back to unknown
    # and render in the gray unknown color instead of raising ValueError.
    unknown = "u"

    keihan_heiban = "H"
    keihan_atamadaka = "A"
    keihan_nakadaka = "N"
    keihan_low_heiban = "L"
    keihan_low_nakadaka = "M"
    keihan_low_odaka = "O"
    keihan_kifuku = "K"


def determine_role_keihan(raw_role: str | None) -> Role:
    """Determine the Keihan dialect pitch role from a raw role character.

    Upper case letters are used for Keihan.
    Invalid role letters fall back to Role.unknown instead of raising ValueError.
    """
    role = str(raw_role or Role.keihan_heiban.value)
    for candidate in (role.upper(), role.lower()):
        try:
            return Role(candidate)
        except ValueError:
            continue
    return Role.unknown


def determine_levels_keihan(accent: SplitAccent, n_moras: int) -> list[PitchLevel]:
    """Build a list of high/low levels for each mora in the Keihan dialect."""
    if not accent.keihan:
        return []
    assert isinstance(accent.levels, str), "levels should be str"
    levels_list = list(str(accent.levels).lower())
    levels_list += [levels_list[-1]] * (n_moras - len(levels_list))
    return [PitchLevel(c.lower()) for c in levels_list]  # construct pitch level from its value.


def guess_role_from_pitch_num(n_moras: int, pitch_n: str | None) -> Role:
    """Infer the pitch accent role from the numeric pitch value and mora count."""
    if not pitch_n:
        return Role.heiban
    pitch_n_int = int(pitch_n)
    if pitch_n_int == 0:
        return Role.heiban
    if pitch_n_int < 0:
        return Role.particle
    if pitch_n_int == 1:
        return Role.atamadaka
    if pitch_n_int == n_moras:
        return Role.odaka
    if pitch_n_int < n_moras:
        return Role.nakadaka
    return Role.heiban


def determine_role_tokyo(sdict: SectionParts, n_moras: int, accent: SplitAccent) -> Role:
    """Determine the Tokyo dialect pitch role from a parsed section dict.

    If `;` but no letter or number, then it defaults to heiban.
    """
    # Note: do NOT check accent.is_particle here.
    # is_particle (the 'p' prefix in notation like 'ぐらい;pa') is a rendering hint
    # that tells the SVG drawer to use unfilled circles. It is stored separately
    # in Section.is_particle and used for CSS class naming. The role itself
    # must reflect the explicit role letter (e.g. 'a' for atamadaka) so that
    # the correct pitch pattern and color are applied.
    # Words without any accent specifier (sep is empty) default to Role.particle.
    if not sdict.sep:
        return Role.particle
    if not accent.role:
        return guess_role_from_pitch_num(n_moras, accent.pitch)

    try:
        return Role(str(accent.role).lower())
    except ValueError:
        # Invalid role letters (e.g. ";z") render as unknown instead of raising.
        return Role.unknown


def is_empty_section(word: str) -> bool:
    """Return True for sections that never enter dialect-specific pitch logic."""
    return not word or word in NON_RENDERED_SECTIONS


class SpecialPitch(enum.Enum):
    always_high = -2
    always_low = -1
    atamadaka = 1
    heiban = 0
    drop_inside = 2


def determine_pitch_tokyo(sdict: SectionParts, n_moras: int, accent: SplitAccent, role: Role) -> int | None:
    """Determine the numeric pitch value for a Tokyo dialect section."""
    if sdict.sep and accent.pitch:
        return int(accent.pitch)

    if role == Role.heiban or role == Role.setsubigo:
        return SpecialPitch.heiban.value
    if role == Role.atamadaka:
        return SpecialPitch.atamadaka.value
    if role == Role.nakadaka or role == Role.kifuku:
        return SpecialPitch.drop_inside.value
    if role == Role.odaka:
        return n_moras
    if role == Role.particle:
        return None
    if role == Role.empty:
        return SpecialPitch.always_low.value

    return SpecialPitch.heiban.value


def adjust_kana(text: str, cfg: JapaneseConfig) -> str:
    """Convert kana to the configured reading format."""
    match cfg.svg_graphs.reading_format:
        case SvgGraphReadingFormat.hiragana:
            return to_hiragana(text)
        case SvgGraphReadingFormat.katakana:
            return to_katakana(text)
    raise ValueError(f"unknown reading format: {cfg.svg_graphs.reading_format.name}")


def prepare_moras(word: str, cfg: JapaneseConfig) -> list[ArtistMora]:
    """Extract the reading from a word, apply kana conversion, then split into morae."""
    reading = furigana_to_reading(word)
    reading = adjust_kana(reading, cfg)
    reading = split_to_moras(reading)
    return reading


def determine_role(sdict: SectionParts, n_moras: int, accent: SplitAccent) -> Role:
    """Determine the rendered role for a parsed Pitch Artist section."""
    if is_empty_section(sdict.word):
        return Role.empty
    if accent.keihan:
        return determine_role_keihan(accent.role)
    return determine_role_tokyo(sdict, n_moras, accent)


@dataclasses.dataclass(frozen=True)
class Section:
    """A parsed word section of a pitch accent expression, holding morae, role, and pitch data."""

    raw: str
    is_keihan: bool
    role: Role
    levels: list[PitchLevel]
    pitch: int | None
    moras: list[ArtistMora]
    word: str

    # 'p' marks a particle.
    # A particle without a pitch number (は;p) renders in the particle color
    # (gray by default). A particle with an explicit pitch accent (まで;pa)
    # renders in the accent's color (atamadaka is red by default),
    # still as hollow dots with no fill.
    is_particle: bool

    # True if this section is a tape connector (dotted line between words).
    # A tape is written as a bare ";" section, e.g. "が ; いい" tapes が to いい.
    # When two words are linked with a solid line, they are welded.
    # A dotted line means they are taped.
    is_tape: bool

    @property
    def class_name(self) -> SvgGraphClassName:
        """Return the pitch role class used for SVG rendering and color lookup."""
        return SvgGraphClassName[self.role.name]


def adjust_ha_wa(moras: list[ArtistMora]) -> list[ArtistMora]:
    """Convert particle は/ハ to わ/ワ for rendered reading text."""
    if len(moras) == 1:
        match moras[0].text:
            case "ハ":
                return [ArtistMora("ワ", flags=moras[0].flags)]
            case "は":
                return [ArtistMora("わ", flags=moras[0].flags)]
    return moras


def clean_non_printable_chars(word: str) -> str:
    """Remove internal notation markers that should not appear in graph comments."""
    return word.replace(DEVOICED_PREFIX, "")


def make_section(raw_section: str, cfg: JapaneseConfig) -> Section:
    """Parse one raw Pitch Artist section and resolve its role, pitch, and mora data."""
    sdict: SectionParts = split_section(raw_section)
    moras = prepare_moras(sdict.word, cfg)
    accent = split_accent(sdict.accent)
    role = determine_role(sdict, len(moras), accent)
    is_particle = bool(accent.is_particle) or role == Role.particle
    if is_particle:
        moras = adjust_ha_wa(moras)
    return Section(
        raw=raw_section,
        is_keihan=bool(accent.keihan),
        role=role,
        levels=determine_levels_keihan(accent, len(moras)),
        pitch=determine_pitch_tokyo(sdict, len(moras), accent, role),
        is_particle=is_particle,
        moras=moras,
        word=clean_non_printable_chars(sdict.word),
        is_tape=(raw_section == TAPE_CONNECTOR),
    )


def set_pitch(section: Section, last_word_ended_low: bool) -> Section:
    """Fill an implicit pitch value based on the previous section's ending pitch."""
    if section.pitch is None:
        return dataclasses.replace(
            section, pitch=SpecialPitch.always_low.value if last_word_ended_low else SpecialPitch.always_high.value
        )
    return section


def calc_level(pitch_num: int, pos: int) -> PitchLevel:
    """Calculate the Tokyo pitch level at a mora position."""
    if pos < pitch_num or pitch_num == SpecialPitch.heiban.value:
        return PitchLevel.high
    else:
        return PitchLevel.low


def build_levels_tokyo(section: Section, last_word_ended_low: bool) -> Section:
    """Build a list of high/low pitch levels for a Tokyo dialect section."""
    section = set_pitch(section, last_word_ended_low)
    result: list[PitchLevel]

    if section.pitch == SpecialPitch.always_low.value:
        result = [PitchLevel.low] * len(section.moras)
    elif section.pitch == SpecialPitch.always_high.value:
        result = [PitchLevel.high] * len(section.moras)
    elif section.pitch == SpecialPitch.atamadaka.value:
        result = [PitchLevel.high, *(PitchLevel.low for _ in section.moras[1:])]
    else:
        result = [PitchLevel.low if last_word_ended_low else PitchLevel.high]
        assert section.pitch is not None
        result.extend(calc_level(section.pitch, index) for index, mora in enumerate(section.moras[1:], start=1))
    return dataclasses.replace(section, levels=result)


def calc_last_word_ended_low(section: Section, last_word_ended_low: bool) -> bool:
    """Determine whether the last mora of a section ended on a low pitch."""
    if section.role == Role.empty and section.word not in PITCH_BREAKS:
        return last_word_ended_low

    if section.pitch == SpecialPitch.atamadaka.value:
        return True

    if section.pitch == SpecialPitch.heiban.value or section.pitch == SpecialPitch.always_high.value:
        return False

    return len(section.moras) >= section.pitch


def build_high_low(sequence: list[Section]) -> Iterable[Section]:
    """Assign high/low pitch levels to every mora in a sequence of sections."""
    last_word_ended_low = True
    for section in sequence:
        if section.is_keihan:
            last_word_ended_low = section.levels[-1] == PitchLevel.low
        else:
            section = build_levels_tokyo(section, last_word_ended_low)
            last_word_ended_low = calc_last_word_ended_low(section, last_word_ended_low)
        yield section


def filter_empty_moras(sequence: list[Section]) -> list[Section]:
    """Remove sections that have no morae, keeping separators and tape connectors."""
    return [
        section
        for section in sequence
        if (
            len(section.moras)
            or section.word in PITCH_BREAKS
            or section.is_tape  # allow tape in, but filter it out later.
        )
    ]


def _color_sentence(sentence: list[Section]) -> str:
    """Wrap each visible word in a sentence with an HTML span colored by its pitch role."""
    result = []
    for section in sentence:
        if section.word in TEXT_HIDDEN or section.is_tape:
            continue
        result.append(f'<span class="{section.role.name}">{section.word}</span>')
    return "".join(result)


def apply_kanji_colors(seq_sequences: list[list[Section]]) -> list[str]:
    """Apply pitch-role-based CSS coloring to kanji words in each sentence."""
    return [_color_sentence(s) for s in seq_sequences]


def is_small_tsu(text: str) -> bool:
    """Return True if text is a small tsu that can inherit the previous pitch level."""
    return text in SMALL_TSU


def mora_level(section: Section, mora: ArtistMora, index: int) -> PitchLevel:
    """Return the already-resolved level for a mora, preserving the small tsu special case."""
    if is_small_tsu(mora.text) and index == 1 and section.levels[index - 1] == PitchLevel.low:
        return section.levels[index - 1]
    return section.levels[index]


def artist_mora_to_graph_mora(section: Section, mora: ArtistMora, index: int) -> SvgGraphMora:
    """Convert one Pitch Artist mora to the generic SVG graph model."""
    return SvgGraphMora(
        text=mora.text,
        level=mora_level(section, mora, index),
        class_attr=' class="devoiced"' if SvgMoraFlag.devoiced in mora.flags else "",
        dx_units=len(mora.text),
        flags=mora.flags,
    )


def has_visible_section_before_tape(previous_sections: Sequence[Section]) -> bool:
    """Return True if a renderable mora section appears before a trailing tape section."""
    sections_before_tape = iter(reversed(previous_sections))
    next(sections_before_tape, None)  # Skip the immediate previous section, which is the tape connector.
    for previous in sections_before_tape:
        if previous.role == Role.empty:
            return False
        if previous.moras:
            return True
    return False


def determine_connection_to_previous(section: Section, previous_sections: Sequence[Section]) -> ConnectToPrevious:
    """Return how section connects to the previous rendered section.

    Notation summary: a bare ";" section tapes the next word with a dashed
    connector (e.g. "が ; いい"), while "|" and other separators break the
    contour completely, producing no connector at all (e.g. "は | てんき").
    Everything else welds adjacent words with a solid connector.
    """
    if not previous_sections:
        return ConnectToPrevious.none
    previous: Section = previous_sections[-1]
    if previous.is_tape and has_visible_section_before_tape(previous_sections):
        return ConnectToPrevious.tape
    if previous.role != Role.empty and section.role != Role.empty:
        return ConnectToPrevious.weld
    return ConnectToPrevious.none


def section_to_graph_section(section: Section, connect_to_previous: ConnectToPrevious) -> SvgGraphWord | None:
    """Convert a renderable Pitch Artist section to the generic SVG graph model."""
    if section.role == Role.empty or section.is_tape:
        return None
    return SvgGraphWord(
        class_name=section.class_name,
        moras=tuple(artist_mora_to_graph_mora(section, mora, index) for index, mora in enumerate(section.moras)),
        is_particle=section.is_particle,
        connect_to_previous=connect_to_previous,
    )


def sections_to_graph(sequence: Sequence[Section]) -> SvgGraph:
    """Convert Pitch Artist sections to a normalized SVG graph."""
    previous_sections: list[Section] = []
    sections: list[SvgGraphWord] = []
    for section in sequence:
        if graph_section := section_to_graph_section(
            section,
            connect_to_previous=determine_connection_to_previous(section, previous_sections),
        ):
            sections.append(graph_section)
        previous_sections.append(section)
    return SvgGraph(sections=sections, outer_class_name=None)


class SvgPitchArtistGraphMaker:
    """Parse Pitch Artist notation and render it as SVG pitch graphs."""

    _renderer: SvgGraphRenderer

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Initialize the maker with Japanese add-on configuration."""
        self._cfg = cfg
        self._renderer = SvgGraphRenderer(self._cfg)

    def _parse_sections(self, sequence: list[str]) -> list[Section]:
        """Parse a list of raw section strings into Section objects."""
        return [make_section(word, cfg=self._cfg) for word in sequence]

    def make_sequences(self, expr: str) -> list[list[Section]]:
        """Parse a pitch accent expression string into a list of section sequences.

        Normalizes the input, splits into sentences, expands multiple pitch notations,
        parses each section, and assigns high/low levels.
        """
        expr = normalize_for_parsing(expr)
        sentences = split_to_sentences(expr)

        sentences = [detach_ghost_particle(sentence) for sentence in sentences]

        sentences_by_sections = list(map(split_to_sections, sentences))
        sentences_by_sections = split_multiple_pitch_notations(sentences_by_sections)

        sequences = [self._parse_sections(section) for section in sentences_by_sections]
        sequences = [list(build_high_low(sequence)) for sequence in sequences]
        return sequences

    def make_graph(self, sequence: list[Section]) -> str | None:
        """Render a sequence of sections as a complete SVG pitch accent graph.

        Returns None if the sequence contains no renderable sections.
        """
        sequence = filter_empty_moras(sequence)
        if not any(section.moras for section in sequence):
            return None
        svg = self._renderer.render_graph(sections_to_graph(sequence))
        notation = f'<!-- generated with expression: "{" ".join(s.raw for s in sequence)}" -->'
        return f"{notation}\n{svg}"

    def make_graphs(self, sequences: list[list[Section]]) -> Iterable[str]:
        """Yield SVG pitch graphs for each non-empty sequence of sections."""
        for sequence in sequences:
            if graph := self.make_graph(sequence):
                yield graph
