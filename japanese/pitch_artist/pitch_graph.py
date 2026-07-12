# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import enum
from collections.abc import Iterable, Sequence
from enum import Enum

from ..config_view import JapaneseConfig, SvgGraphReadingFormat
from ..mecab_controller import to_hiragana, to_katakana
from ..pitch_accents.svg_graph_renderer import SvgGraphRenderer
from ..pitch_accents.svg_graph_types import (
    PitchLevel,
    SvgGraph,
    SvgGraphMora,
    SvgGraphSection,
    SvgMoraFlag,
)
from .split import (
    DEVOICED_PREFIX,
    GHOST_PARTICLE,
    PITCH_BREAKS,
    SENT_HIDDEN,
    SEPARATORS,
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

    keihan_heiban = "H"
    keihan_atamadaka = "A"
    keihan_nakadaka = "N"
    keihan_low_heiban = "L"
    keihan_low_nakadaka = "M"
    keihan_low_odaka = "O"
    keihan_kifuku = "K"


def is_empty_particle(word: str) -> bool:
    """Return True if the word is a separator character with no pitch content.

    Separators (| , 、) are functionally identical — they disconnect adjacent
    words and produce no visible elements in the graph.
    """
    return word in SEPARATORS


def determine_role_keihan(raw_role: str | None) -> Role:
    """Determine the Keihan dialect pitch role from a raw role character.

    Upper case letters are used for Keihan.
    """
    role = str(raw_role or Role.keihan_heiban.value)
    try:
        return Role(role.upper())
    except ValueError:
        return Role(role.lower())


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

    If nothing at all => particle.
    If `;` but no letter or number, then it defaults to heiban.
    """
    if n_moras < 1 or is_empty_particle(sdict.word):
        return Role.empty
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

    return Role(str(accent.role).lower())


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


def determine_role(sdict: SectionParts, moras: list[ArtistMora], accent: SplitAccent) -> Role:
    if accent.keihan:
        return determine_role_keihan(accent.role)
    return determine_role_tokyo(sdict, len(moras), accent)


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
    # For example, まで is an atamadaka particle,
    # so rather than just representing it as gray dots with no fill,
    # I would like to represent it as red dots with no fill.
    is_particle: bool

    # True if this section is a tape connector (dotted line between words).
    # When two words are linked with a solid line, they are welded.
    # A dotted line means they are taped.
    is_tape: bool

    @property
    def class_name(self) -> str:
        """Return the CSS class name for SVG rendering based on the section's role."""
        if self.is_particle and self.role != Role.particle:
            return f"{Role.particle.name} {self.role.name}"
        return self.role.name


def adjust_ha_wa(moras: list[ArtistMora]) -> list[ArtistMora]:
    if len(moras) == 1:
        match moras[0].text:
            case "ハ":
                return [ArtistMora("ワ", flags=moras[0].flags)]
            case "は":
                return [ArtistMora("わ", flags=moras[0].flags)]
    return moras


def clean_non_printable_chars(word: str) -> str:
    return word.replace(DEVOICED_PREFIX, "")


def make_section(raw_section: str, cfg: JapaneseConfig) -> Section:
    sdict: SectionParts = split_section(raw_section)
    moras = prepare_moras(sdict.word, cfg)
    accent = split_accent(sdict.accent)
    role = determine_role(sdict, moras, accent)
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
        is_tape=(raw_section == ";"),
    )


def set_pitch(section: Section, last_word_ended_low: bool) -> Section:
    if section.pitch is None:
        return dataclasses.replace(
            section, pitch=SpecialPitch.always_low.value if last_word_ended_low else SpecialPitch.always_high.value
        )
    return section


def calc_level(pitch_num: int, pos: int) -> PitchLevel:
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


def should_connect(section: Section, prev_section: Section) -> bool:
    """Return True if the current section should be connected to the previous one by a line.

    By default, all dots are connected by lines.
    Everything is connected unless you specifically add , or |.
    """
    if prev_section.is_tape:
        # if section is a tape, it is not printed on the svg
        # but connects two moras around itself with a dotted line.
        # Tape is skipped, so you only need to test prev_section.
        return True
    if section.role == Role.empty or prev_section.role == Role.empty:
        return False
    return True


def _color_sentence(sentence: list[Section]) -> str:
    """Wrap each visible word in a sentence with an HTML span colored by its pitch role."""
    result = []
    for section in sentence:
        if section.word in SENT_HIDDEN or section.is_tape:
            continue
        result.append(f'<span class="{section.role.name}">{section.word}</span>')
    return "".join(result)


def apply_kanji_colors(seq_sequences: list[list[Section]]) -> list[str]:
    """Apply pitch-role-based CSS coloring to kanji words in each sentence."""
    return [_color_sentence(s) for s in seq_sequences]


class SvgPitchArtistGraphMaker:
    def __init__(self, cfg: JapaneseConfig) -> None:
        self._cfg = cfg
        self._mk = SvgPitchGraphMaker(self._cfg.svg_graphs)

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

    def _calc_svg_width(self, sequence: list[Section], morae_width: int) -> int:
        """Calculate the total SVG width in pixels for a sequence of sections."""
        return (
            sum(len(section.moras) if section.role != Role.empty else 0 for section in sequence) * morae_width
            + self._cfg.svg_graphs.graph_horizontal_padding * 2
        )

    def _make_text(self, text: str, pos: Point, dx: int) -> str:
        """Generate an SVG <text> element for a mora label."""
        class_name = ' class="devoiced"' if isinstance(text, DevoicedMora) else ""
        return self._mk.make_text_element(text, pos, class_name, dx)

    def make_graph(self, sequence: list[Section]) -> str | None:
        """Render a sequence of sections as a complete SVG pitch accent graph.

        Returns None if the sequence contains no renderable sections.
        """
        sequence = filter_empty_moras(sequence)
        if not any(section.moras for section in sequence):
            return None

        height_high = self._cfg.svg_graphs.size_unit
        hor_pad = self._cfg.svg_graphs.graph_horizontal_padding
        x_step = self._cfg.svg_graphs.x_step
        height_low = height_high + self._cfg.svg_graphs.graph_height
        height_kana = height_low + x_step

        pos = Point.new(x=height_high + hor_pad, y=height_high)

        circles, paths, text = [], [], []

        for i, section in enumerate(sequence):
            # each section is a word, a list of moras
            if section.role == Role.empty or section.is_tape:
                continue

            word_circles, text_moras = [], []
            path = Path(self._cfg.svg_graphs)
            connector = Line(self._cfg.svg_graphs)  # single connector per section

            if 0 < i < len(sequence) and should_connect(section, sequence[i - 1]):
                connector.start_at(pos.shift_by(x=-x_step), tape=sequence[i - 1].is_tape)

            for j, mora in enumerate(section.moras):
                mora_level = (
                    section.levels[j - 1]
                    if mora in ("っ", "ッ") and j == 1 and section.levels[j - 1] == PitchLevel.low
                    else section.levels[j]
                )
                pos = pos.replace(y=height_high if mora_level == PitchLevel.high else height_low)
                word_circles.append(self._mk.make_circle(pos.replace()))
                path.push(pos.replace(), is_trailing=False)

                if j == 0 and connector.is_unfinished():
                    # first mora of a word
                    connector.end_at(pos.replace())

                if mora != GHOST_PARTICLE:
                    if isinstance(mora, DevoicedMora):
                        # added some magic numbers here because it's unclear how the position is calculated.
                        # possibly, it's font-dependent.
                        text_moras.append(
                            self._mk.make_devoiced_circle(pos.replace(y=height_kana), extend=len(mora) > 1)
                        )
                    text_moras.append(
                        self._make_text(mora, pos.replace(y=height_kana), int(self._cfg.svg_graphs.text_dx) * len(mora))
                    )

                pos = pos.shift_by(x=x_step)

            circles.append(make_group(word_circles, section.class_name))
            paths.append(make_group([path.draw()], section.class_name))
            text.append(make_group(text_moras, section.class_name))

            if connector.is_completed():
                paths.append(
                    make_group([connector.adjust_to_radius(self._cfg.svg_graphs.circle_radius).draw()], "connector")
                )

        content = [
            make_group(paths, "paths"),
            make_group(circles, "circles"),
        ]
        svg_width = self._calc_svg_width(sequence, x_step)

        svg_height_with_text = height_kana + self._cfg.svg_graphs.size_unit
        svg_height_no_text = height_low + self._cfg.svg_graphs.size_unit

        if not self._cfg.svg_graphs.include_text:
            svg_height = svg_height_no_text
            ratio = svg_height_no_text / svg_height_with_text
            visible_height = int(ratio * self._cfg.svg_graphs.graph_visible_height)
        else:
            svg_height = svg_height_with_text
            visible_height = self._cfg.svg_graphs.graph_visible_height
            content.append(make_group(text, "text"))

        svg = self._mk.make_svg("".join(content), width=svg_width, height=svg_height, visible_height=visible_height)
        notation = f'<!-- generated with expression: "{" ".join(s.raw for s in sequence)}" -->'

        return f"{notation}\n{svg}"

    def make_graphs(self, sequences: list[list[Section]]) -> Iterable[str]:
        """Yield SVG pitch graphs for each non-empty sequence of sections."""
        for sequence in sequences:
            if graph := self.make_graph(sequence):
                yield graph
