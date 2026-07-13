# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import typing
from collections.abc import Sequence

from ..config_view import SvgPitchGraphOptionsConfigView
from .svg_components import Line, Path, Point, attrs_circle, make_group
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
        return make_group(content, graph.outer_class_name)
    return "".join(content)


class SvgGraphRenderer:
    """Render normalized pitch graph data as SVG markup."""

    _opts: SvgPitchGraphOptionsConfigView

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options

    @property
    def hor_pad(self) -> int:
        """Return the horizontal padding around the graph."""
        return self._opts.graph_horizontal_padding

    @property
    def height_high(self) -> int:
        """Return the y-coordinate for a high-pitch mora."""
        return self._opts.size_unit

    @property
    def height_low(self) -> int:
        """Return the y-coordinate for a low-pitch mora."""
        return self.height_high + self._opts.graph_height

    @property
    def height_kana(self) -> int:
        """Return the y-coordinate for mora text."""
        return self.height_low + self._opts.x_step

    def make_circle(self, pos: Point, is_trailing: bool, is_particle: bool) -> str:
        """Create a circle positioned where two pitch lines touch."""
        return (
            f"<circle {attrs_circle(is_trailing=is_trailing, is_particle=is_particle)} "
            f'stroke-width="{self._opts.stroke_width:.2f}" '
            f'cx="{pos.x:.3f}" cy="{pos.y:.3f}" r="{self._opts.circle_radius:.2f}" />'
        )

    def make_devoiced_circle(self, pos: Point, multi_char: bool) -> str:
        """
        Create a dashed circle around devoiced mora text.
        If multi_char is true, widen the circle. This is needed if the mora consists of two characters.
        """
        if not multi_char:
            pos = pos.shift_by(
                x=self._opts.font_size / 2 + self._opts.text_dx,
                y=-self._opts.font_size / 2 + self._opts.devoiced_circle_dy,
            )
            return (
                f'<circle class="devoiced" fill="none" stroke="black" cx="{pos.x:.0f}" cy="{pos.y:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" r="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_dasharray}" />'
            )
        else:
            pos = pos.shift_by(
                x=-self._opts.font_size / 2 - self._opts.devoiced_rectangle_padding + self._opts.text_dx,
                y=-self._opts.font_size / 2 - self._opts.devoiced_circle_radius + self._opts.devoiced_circle_dy,
            )
            width = self._opts.font_size * 2 + self._opts.devoiced_rectangle_padding * 2
            height = self._opts.devoiced_circle_radius * 2
            return (
                f'<rect class="devoiced" fill="none" stroke="black" x="{pos.x:.0f}" y="{pos.y:.0f}" '
                f'width="{width:.0f}" height="{height:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" rx="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_dasharray}" />'
            )

    def make_text_element(self, text: str, pos: Point, class_attr: str, dx: int) -> str:
        """Create an SVG text element from preformatted text content and class attributes."""
        return (
            f'<text{class_attr} fill="black" '
            f'font-size="{self._opts.font_size:.1f}px" '
            f'letter-spacing="{self._opts.letter_spacing:.1f}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{text}</text>'
        )

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        """Wrap SVG child markup in the pitch graph SVG element."""
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._opts.graph_font_name}" '
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

    def _start_connector(self, section: SvgGraphWord, pos: Point) -> Line:
        connector = Line(self._opts)
        match section.connect_to_previous:
            case ConnectToPrevious.weld:
                connector.start_at(pos.shift_by(x=-self._opts.x_step), tape=False)
            case ConnectToPrevious.tape:
                connector.start_at(pos.shift_by(x=-self._opts.x_step), tape=True)
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
        path = Path(self._opts)
        connector = self._start_connector(section, pos)
        for idx, mora in enumerate(section.moras):
            pos = pos.replace(y=self.height_high if mora.level == PitchLevel.high else self.height_low)
            # Note: is_particle is always False for FormattedEntry-derived sections.
            word_circles.append(
                self.make_circle(
                    pos.replace(),
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
                    )
                )
            # If this mora is trailing (FormattedEntry path) or is a ghost particle (Pitch Artist path),
            # then no text should be printed.
            if not mora.is_text_hidden:
                text_moras.append(
                    self.make_text_element(
                        mora.text,
                        pos.replace(y=self.height_kana),
                        mora.class_attr,
                        self._opts.text_dx * mora.dx_units,
                    )
                )
            pos = pos.shift_by(x=self._opts.x_step)

        # Note: connectors are never used with FormattedEntry-derived sections.
        connector_svg = (
            make_group(
                [connector.adjust_to_radius(self._opts.circle_radius).draw()],
                "connector",
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
            paths.append(make_group([rendered.path], section.class_name))
            if rendered.connector:
                paths.append(rendered.connector)
            circles.append(make_group([rendered.circles], section.class_name))
            text.append(make_group([rendered.text], section.class_name))
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
        if self._opts.include_text:
            svg_height = svg_height_with_text
            visible_height = self._opts.graph_visible_height
        else:
            svg_height = svg_height_no_text
            # Preserve the same viewBox-to-CSS-pixel scale when kana text is hidden.
            visible_height_ratio = svg_height_no_text / svg_height_with_text
            visible_height = int(visible_height_ratio * self._opts.graph_visible_height)
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
            sum(len(section.moras) for section in sections) * self._opts.x_step
            + self._opts.graph_horizontal_padding * 2
        )
