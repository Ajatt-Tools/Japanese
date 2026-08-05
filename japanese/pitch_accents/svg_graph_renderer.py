# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import typing
from collections.abc import Sequence

from ..config_view import JapaneseConfig
from .colors import SvgGraphClassName
from .svg_components import (
    Line,
    Path,
    Point,
    SvgBlackAndWhiteRole,
    lookup_component_color,
    make_group,
    trail_color,
)
from .svg_graph_types import (
    ConnectToPrevious,
    PitchLevel,
    SvgGraph,
    SvgGraphWord,
    SvgMoraFlag,
)


class RenderedSection(typing.NamedTuple):
    path: str
    circles: str
    text: str
    connector: str
    # Position where the next section should start drawing.
    pos: Point


class RenderedGraphComponents(typing.NamedTuple):
    lines: str
    circles: str
    text: str


def wrap_content(graph: SvgGraph, content: RenderedGraphComponents) -> str:
    """Wrap ungrouped graphs in their pitch-type group while leaving artist graphs unwrapped."""
    if graph.outer_class_name:
        return make_group(content, graph.outer_class_name.name)
    return "".join(content)


def section_css_class(section: SvgGraphWord) -> str:
    """Return the CSS class string for a section, adding particle for compound particle roles."""
    if section.is_particle and section.class_name != SvgGraphClassName.particle:
        return f"{SvgGraphClassName.particle.name} {section.class_name.name}"
    return section.class_name.name


def attrs_circle(*, is_trailing: bool, is_particle: bool, circle_color: str) -> str:
    """Return SVG circle attributes for pitch points using an already-resolved color."""
    if is_trailing:
        return f'class="{SvgBlackAndWhiteRole.trail.name}" fill="none" stroke="{circle_color}"'
    if is_particle:
        return f'fill="none" stroke="{circle_color}"'
    return f'fill="{circle_color}" stroke="{circle_color}"'


class SvgGraphRenderer:
    """Render normalized pitch graph data as SVG markup."""

    _cfg: JapaneseConfig

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Initialize the renderer with the add-on configuration."""
        self._cfg = cfg

    @property
    def hor_pad(self) -> int:
        """Return the horizontal padding around the graph."""
        return self._cfg.svg_graphs.graph_horizontal_padding

    @property
    def height_high(self) -> int:
        """Return the y-coordinate for a high-pitch mora."""
        return self._cfg.svg_graphs.size_unit

    @property
    def height_low(self) -> int:
        """Return the y-coordinate for a low-pitch mora."""
        return self.height_high + self._cfg.svg_graphs.graph_height

    @property
    def height_kana(self) -> int:
        """Return the y-coordinate for mora text."""
        return self.height_low + self._cfg.svg_graphs.x_step

    def make_circle(self, pos: Point, *, is_trailing: bool, is_particle: bool, circle_color: str) -> str:
        """Create a circle positioned where two pitch lines touch."""
        return (
            f"<circle {attrs_circle(is_trailing=is_trailing, is_particle=is_particle, circle_color=circle_color)} "
            f'stroke-width="{self._cfg.svg_graphs.stroke_width:.2f}" '
            f'cx="{pos.x:.3f}" cy="{pos.y:.3f}" r="{self._cfg.svg_graphs.circle_radius:.2f}" />'
        )

    def _circle_color_for_mora(self, *, is_trailing: bool, is_particle: bool, word_color: str) -> str:
        """Resolve the final circle color for one mora."""
        if is_trailing:
            return trail_color(self._cfg)
        if is_particle:
            return lookup_component_color(self._cfg, SvgBlackAndWhiteRole.word, SvgGraphClassName.particle)
        return word_color

    def make_devoiced_circle(self, pos: Point, *, multi_char: bool, circle_color: str) -> str:
        """
        Create a dashed circle around devoiced mora text.
        If multi_char is true, widen the circle. This is needed if the mora consists of two characters.
        """
        font_size = self._cfg.svg_graphs.font_size
        stroke_width = self._cfg.svg_graphs.devoiced_circle_width
        r = self._cfg.svg_graphs.devoiced_circle_radius
        dasharray = self._cfg.svg_graphs.devoiced_stroke_dasharray

        if not multi_char:
            pos = pos.shift_by(
                x=font_size / 2 + self._cfg.svg_graphs.text_dx,
                y=-font_size / 2 + self._cfg.svg_graphs.devoiced_circle_dy,
            )
            return (
                f'<circle class="devoiced" fill="none" stroke="{circle_color}" cx="{pos.x:.0f}" cy="{pos.y:.0f}" '
                f'stroke-width="{stroke_width:.2f}" r="{r:.2f}" '
                f'stroke-dasharray="{dasharray}" />'
            )
        else:
            pos = pos.shift_by(
                x=-font_size / 2 - self._cfg.svg_graphs.devoiced_rectangle_padding + self._cfg.svg_graphs.text_dx,
                y=-font_size / 2 - r + self._cfg.svg_graphs.devoiced_circle_dy,
            )
            width = self._cfg.svg_graphs.font_size * 2 + self._cfg.svg_graphs.devoiced_rectangle_padding * 2
            height = r * 2
            return (
                f'<rect class="devoiced" fill="none" stroke="{circle_color}" x="{pos.x:.0f}" y="{pos.y:.0f}" '
                f'width="{width:.0f}" height="{height:.0f}" '
                f'stroke-width="{stroke_width:.2f}" rx="{r:.2f}" '
                f'stroke-dasharray="{dasharray}" />'
            )

    def make_text_element(self, text: str, *, pos: Point, class_attr: str, dx: int, text_color: str) -> str:
        """Create an SVG text element from preformatted text content and class attributes."""
        # Keep fill as a presentation-attribute fallback. CSS color mode loads
        # stylesheet rules that override presentation attributes through the cascade.
        return (
            f'<text{class_attr} fill="{text_color}" '
            f'font-size="{self._cfg.svg_graphs.font_size:.1f}px" '
            f'letter-spacing="{self._cfg.svg_graphs.letter_spacing:.1f}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{text}</text>'
        )

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        """Wrap SVG child markup in the pitch graph SVG element."""
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._cfg.svg_graphs.graph_font_name}" '
            f'viewBox="0 0 {width:d} {height:d}" height="{visible_height:d}px" '
            f'xmlns="http://www.w3.org/2000/svg">{contents}</svg>'
        )

    def render_graph(self, graph: SvgGraph) -> str:
        """Render a normalized pitch graph as SVG markup.

        Dictionary-entry graphs have an outer pitch-type class
        (e.g. 'heiban', 'nakadaka') and are rendered as one section.
        Pitch Artist graphs leave sections grouped individually
        so particles and accent colors can be styled independently.
        """
        start_pos = Point.new(x=self.height_high + self.hor_pad, y=self.height_high)

        if graph.outer_class_name:
            # FormattedEntry-derived graph: one section, wrapped in a pitch-type class.
            content = self._make_dictionary_entry_content(graph, start_pos)
        else:
            # Pitch Artist path
            content = self._make_pitch_artist_content(graph, start_pos)
        return self._make_sized_svg(graph, content)

    def _start_connector(self, section: SvgGraphWord, pos: Point, class_name: SvgGraphClassName) -> Line:
        connector = Line(self._cfg, class_name).set_trailing(section.starts_with_trailing_mora)
        match section.connect_to_previous:
            case ConnectToPrevious.weld:
                connector.start_at(pos.shift_by(x=-self._cfg.svg_graphs.x_step), tape=False)
            case ConnectToPrevious.tape:
                connector.start_at(pos.shift_by(x=-self._cfg.svg_graphs.x_step), tape=True)
            case ConnectToPrevious.none:
                pass
        return connector

    def _render_section(self, section: SvgGraphWord, pos: Point) -> RenderedSection:
        """Render one section, starting at the given drawing position.

        pos is the (x, y) where the first mora of this section should be drawn.
        The returned RenderedSection.pos is where the next section should start.
        """
        word_circles: list[str] = []
        text_moras: list[str] = []
        path = Path(self._cfg, section.class_name)
        connector = self._start_connector(section, pos, SvgGraphClassName.connector)
        word_color = lookup_component_color(self._cfg, SvgBlackAndWhiteRole.word, section.class_name)

        for idx, mora in enumerate(section.moras):
            pos = pos.replace(y=self.height_high if mora.level == PitchLevel.high else self.height_low)
            # Note: is_particle is always False for FormattedEntry-derived sections.
            word_circles.append(
                self.make_circle(
                    pos.replace(),
                    circle_color=self._circle_color_for_mora(
                        is_trailing=mora.is_trailing,
                        is_particle=section.is_particle,
                        word_color=word_color,
                    ),
                    is_trailing=mora.is_trailing,
                    is_particle=section.is_particle,
                )
            )
            path.push(pos.replace(), is_trailing=mora.is_trailing)
            # Note: connectors are never used with FormattedEntry-derived sections.
            if idx == 0 and connector.is_unfinished():
                connector.end_at(pos.replace())
            if SvgMoraFlag.devoiced in mora.flags:
                text_moras.append(
                    self.make_devoiced_circle(
                        pos.replace(y=self.height_kana),
                        multi_char=mora.is_multi_char,
                        circle_color=word_color,
                    )
                )
            # If this mora is trailing (FormattedEntry path) or is a ghost particle (Pitch Artist path),
            # then no text should be printed.
            if not mora.is_text_hidden:
                text_moras.append(
                    self.make_text_element(
                        mora.text,
                        pos=pos.replace(y=self.height_kana),
                        class_attr=mora.class_attr,
                        dx=self._cfg.svg_graphs.text_dx * mora.dx_units,
                        text_color=word_color,
                    )
                )
            pos = pos.shift_by(x=self._cfg.svg_graphs.x_step)

        # Note: connectors are never used with FormattedEntry-derived sections.
        connector_svg = (
            make_group(
                [connector.adjust_to_radius().draw()],
                SvgGraphClassName.connector.name,
            )
            if connector.is_completed()
            else ""
        )

        return RenderedSection(
            path=path.draw(), circles="".join(word_circles), text="".join(text_moras), connector=connector_svg, pos=pos
        )

    def _make_pitch_artist_content(self, graph: SvgGraph, start_pos: Point) -> RenderedGraphComponents:
        """Render Pitch Artist content with per-section SVG groups.

        Pitch Artist graphs may contain multiple words, particles, separators,
        and connector lines. Each section keeps its own CSS class so particles
        and accent colors can be styled independently.
        """
        paths: list[str] = []
        circles: list[str] = []
        text: list[str] = []

        for section in graph.sections:
            rendered = self._render_section(section, start_pos)
            paths.append(make_group([rendered.path], section_css_class(section)))
            if rendered.connector:
                paths.append(rendered.connector)
            circles.append(make_group([rendered.circles], section_css_class(section)))
            text.append(make_group([rendered.text], section_css_class(section)))
            start_pos = rendered.pos

        return RenderedGraphComponents(
            lines=make_group(paths, "lines"),
            circles=make_group(circles, "circles"),
            text=make_group(text, "text"),
        )

    def _make_dictionary_entry_content(self, graph: SvgGraph, start_pos: Point) -> RenderedGraphComponents:
        """Render a dictionary pitch entry as one grouped pitch pattern.

        Dictionary entries are already normalized to one section and are later
        wrapped in a single outer class such as 'heiban' or 'nakadaka'.
        """
        assert len(graph.sections) == 1, "FormattedEntry-derived graph must have only one section."
        rendered = self._render_section(graph.sections[0], pos=start_pos)
        return RenderedGraphComponents(
            lines=make_group([rendered.path], "lines"),
            circles=make_group([rendered.circles], "circles"),
            text=make_group([rendered.text], "text"),
        )

    def _make_sized_svg(self, graph: SvgGraph, content: RenderedGraphComponents) -> str:
        """Apply text visibility settings and SVG dimensions to content groups."""
        svg_height_with_text = self.height_high + self.height_kana
        svg_height_no_text = self.height_high + self.height_low
        if self._cfg.svg_graphs.include_text:
            svg_height = svg_height_with_text
            visible_height = self._cfg.svg_graphs.graph_visible_height
        else:
            svg_height = svg_height_no_text
            # Preserve the same viewBox-to-CSS-pixel scale when kana text is hidden.
            visible_height_ratio = svg_height_no_text / svg_height_with_text
            visible_height = int(visible_height_ratio * self._cfg.svg_graphs.graph_visible_height)
            # Remove text
            content = RenderedGraphComponents(lines=content.lines, circles=content.circles, text="")
        return self.make_svg(
            wrap_content(graph, content),
            width=self._calc_svg_width(graph.sections),
            height=svg_height,
            visible_height=visible_height,
        )

    def _calc_svg_width(self, sections: Sequence[SvgGraphWord]) -> int:
        """Calculate SVG width for all normalized morae."""
        # SvgGraphWord instances are already renderable sections; adapter code
        # filters out separators and tape markers before constructing SvgGraph.
        return (
            sum(len(section.moras) for section in sections) * self._cfg.svg_graphs.x_step
            + self._cfg.svg_graphs.graph_horizontal_padding * 2
        )
