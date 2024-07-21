# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import typing
from collections.abc import Iterable
from math import sqrt
from typing import Optional

from ..config_view import SvgPitchGraphOptionsConfigView
from .basic_types import pitch_type_from_pitch_num
from .common import FormattedEntry
from .entry_to_moras import (
    Mora,
    MoraFlag,
    PitchLevel,
    Quark,
    entry_to_moras,
    mora_flags2class_name,
)


@enum.unique
class SvgColor(enum.Enum):
    trail = "gray"
    word = "black"
    nasal = "red"


def append_class_name(mora_flag: MoraFlag) -> str:
    class_name = mora_flags2class_name(mora_flag)
    return f' class="{class_name}"' if class_name else ""


def make_group(elements: Iterable[str], class_name: str) -> str:
    return f'<g class="{class_name}">{"".join(elements)}</g>'


class Point(typing.NamedTuple):
    x: float
    y: float

    def shift_by(self, *, x: float = 0, y: float = 0):
        return Point(x=self.x + x, y=self.y + y)

    def replace(self, *, x: Optional[float] = None, y: Optional[float] = None):
        return Point(x=x if x is not None else self.x, y=y if y is not None else self.y)


class Line:
    _opts: SvgPitchGraphOptionsConfigView
    is_trailing: bool
    start: Optional[Point]
    end: Optional[Point]

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self.is_trailing = False
        self.start = None
        self.end = None

    def start_at(self, pos: Point) -> "Line":
        self.start = pos
        return self

    def end_at(self, pos: Point) -> "Line":
        self.end = pos
        return self

    def is_completed(self) -> bool:
        return self.start is not None and self.end is not None

    def draw(self) -> str:
        assert self.start is not None and self.end is not None

        def attrs_line() -> str:
            if self.is_trailing:
                return f'class="{SvgColor.trail.name}" stroke="{SvgColor.trail.value}"'
            return f'stroke="{SvgColor.word.value}"'

        return (
            f'<line {attrs_line()} stroke-width="{self._opts.stroke_width:.2f}" '
            f'x1="{self.start.x:.3f}" y1="{self.start.y:.3f}" '
            f'x2="{self.end.x:.3f}" y2="{self.end.y:.3f}" />'
        )

    def adjust_to_radius(self, r: float) -> "Line":
        assert self.start is not None and self.end is not None

        opts = self._opts
        tan = opts.graph_height / opts.x_step
        sin = tan / sqrt(1 + tan * tan)
        cos = 1 / sqrt(1 + tan * tan)

        offset_y = r * sin
        offset_x = r * cos

        if self.start.y == self.end.y:
            self.start = self.start.shift_by(x=r)
            self.end = self.end.shift_by(x=-r)
        elif self.start.y > self.end.y:
            self.start = self.start.shift_by(x=offset_x, y=-offset_y)
            self.end = self.end.shift_by(x=-offset_x, y=offset_y)
        elif self.start.y < self.end.y:
            self.start = self.start.shift_by(x=offset_x, y=offset_y)
            self.end = self.end.shift_by(x=-offset_x, y=-offset_y)

        return self


class Path:
    _opts: SvgPitchGraphOptionsConfigView
    _lines: list[Line]

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self._lines = []

    @property
    def last(self) -> Line:
        return self._lines[-1]

    def start_at(self, pos: Point) -> "Path":
        self._lines.append(Line(self._opts).start_at(pos))
        return self

    def go_to(self, pos: Point) -> "Path":
        self.last.end_at(pos)
        return self

    def push(self, pos: Point, is_trailing: bool) -> "Path":
        if len(self._lines) == 0:
            self.start_at(pos)
        elif self.last.is_completed():
            assert self.last.end
            self.start_at(self.last.end)
            self.go_to(pos)
        else:
            self.go_to(pos)
        self.last.is_trailing = is_trailing
        return self

    def draw(self) -> str:
        opts = self._opts
        drawn: list[str] = []
        line: Line
        for line in filter(lambda _line: _line.is_completed(), self._lines):
            drawn.append(line.adjust_to_radius(opts.circle_radius).draw())
        return "".join(drawn)


class SvgPitchGraphMaker:
    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options

    def make_circle(self, pos: Point, is_trailing: bool = False) -> str:
        """
        Create a circle that is positioned where two lines touch.
        """

        def attrs_circle() -> str:
            if is_trailing:
                return f'class="{SvgColor.trail.name}" fill="none" stroke="{SvgColor.trail.value}"'
            return f'fill="{SvgColor.word.value}" stroke="{SvgColor.word.value}"'

        return (
            f'<circle {attrs_circle()} stroke-width="{self._opts.stroke_width:.2f}" '
            f'cx="{pos.x:.3f}" cy="{pos.y:.3f}" r="{self._opts.circle_radius:.2f}" />'
        )

    def make_devoiced_circle(self, mora: Mora, pos: Point) -> str:
        """
        Make a circle around the mora text to show that it's devoiced.
        """
        if len(mora.txt) == 1:
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

    def quark_to_tspan(self, quark: Quark) -> str:
        assert isinstance(quark, Quark)
        return (
            f'<tspan{append_class_name(quark.flags)} fill="{SvgColor.nasal.value}" '
            f'dx="{self._opts.tspan_dx:.0f}">{quark.txt}</tspan>'
        )

    def assemble_txt_content(self, mora_txt: list[typing.Union[Quark, str]]) -> str:
        return "".join(txt if isinstance(txt, str) else self.quark_to_tspan(txt) for txt in mora_txt)

    def make_text(self, mora: Mora, pos: Point, dx: int) -> str:
        """
        Create a text element with the mora inside.
        """
        assert not mora.is_trailing()
        return (
            f'<text{append_class_name(mora.flags)} fill="black" '
            f'font-size="{self._opts.font_size:.1f}px" '
            f'letter-spacing="{self._opts.letter_spacing:.1f}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{self.assemble_txt_content(mora.txt)}</text>'
        )

    def calc_svg_width(self, moras: list[Mora]) -> int:
        return len(moras) * self._opts.x_step + self._opts.graph_horizontal_padding * 2

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._opts.graph_font}" viewBox="0 0 {width} {height}" '
            f'height="{visible_height}px" xmlns="http://www.w3.org/2000/svg">{contents}</svg>'
        )

    def calc_text_dx(self, mora: Mora) -> int:
        return int(self._opts.text_dx) * sum(1 for char in mora.txt if isinstance(char, str))

    def make_graph(self, entry: FormattedEntry) -> str:
        opts = self._opts
        seq = entry_to_moras(entry)

        height_high = opts.size_unit
        height_low = height_high + opts.graph_height
        height_kana = height_low + opts.x_step
        pos = Point(x=opts.size_unit + opts.graph_horizontal_padding, y=opts.size_unit)

        word_circles: list[str] = []
        text_moras: list[str] = []
        path = Path(opts)

        for idx, mora in enumerate(seq.moras):
            pos = pos.replace(y=height_high if mora.level == PitchLevel.high else height_low)
            word_circles.append(self.make_circle(pos, is_trailing=mora.is_trailing()))
            path.push(pos, is_trailing=mora.is_trailing())

            if MoraFlag.devoiced in mora.flags:
                # circle around text
                text_moras.append(self.make_devoiced_circle(mora, pos.replace(y=height_kana)))

            if not mora.is_trailing():
                text_moras.append(self.make_text(mora, pos.replace(y=height_kana), dx=self.calc_text_dx(mora)))

            pos = pos.shift_by(x=opts.x_step)

        content: list[str] = [
            make_group([path.draw()], "lines"),
            make_group(word_circles, "circles"),
        ]

        svg_width = self.calc_svg_width(seq.moras)
        svg_height_with_text = height_kana + opts.size_unit

        if opts.include_text:
            svg_height = svg_height_with_text
            visible_height = opts.graph_visible_height
            content.append(make_group(text_moras, "text"))
        else:
            svg_height = height_low + opts.size_unit
            ratio = svg_height / svg_height_with_text
            visible_height = int(ratio * opts.graph_visible_height)

        return self.make_svg(
            make_group(content, seq.pitch_type.name),
            width=svg_width,
            height=svg_height,
            visible_height=visible_height,
        )
