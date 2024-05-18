# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import math
import typing
from collections.abc import Iterable
from enum import Enum
from math import sqrt
from typing import Optional

from .common import FormattedEntry
from .entry_to_moras import entry_to_moras, PitchLevel, MoraFlag, Mora, mora_flags_to_classname


@dataclasses.dataclass
class SvgPitchGraphOptions:
    graph_horizontal_padding: int = 6
    size_unit: int = 25
    x_step: int = 50
    graph_height: int = 40
    include_text: bool = True
    stroke_width: float = 2.5
    circle_radius: float = 5.25
    font_size: float = 24
    text_dx: int = -12
    tspan_dx: int = -3
    devoiced_circle_width: float = 1.5
    devoiced_circle_radius: float = 17
    devoiced_rectangle_padding: float = 5
    devoiced_stroke_disarray: str = "2 3"
    graph_visible_height: int = 100
    graph_font: str = "Noto Sans, Noto Sans CJK JP, IPAexGothic, IPAPGothic, IPAGothic, Yu Gothic, Sans, Sans-Serif"


def append_classname(mora_flag: MoraFlag) -> str:
    class_name = mora_flags_to_classname(mora_flag)
    return f' class="{class_name}"' if class_name else ""


@enum.unique
class PitchType(Enum):
    heiban = "h"
    atamadaka = "a"
    nakadaka = "n"
    odaka = "o"
    kifuku = "k"
    unknown = "u"


def pitch_type_from_pitch_num(moras: list[Mora], pitch_num_as_str: str) -> PitchType:
    if not pitch_num_as_str:
        return PitchType.unknown

    try:
        pitch_num = int(pitch_num_as_str)
    except ValueError:
        return PitchType.unknown

    if pitch_num == 0:
        return PitchType.heiban
    if pitch_num == 1:
        return PitchType.atamadaka
    if pitch_num == len(moras):
        return PitchType.odaka
    if pitch_num < len(moras):
        return PitchType.nakadaka
    return PitchType.unknown


def make_group(elements: Iterable[str], classname: str) -> str:
    return f'<g class="{classname}">{"".join(elements)}</g>'


class Point(typing.NamedTuple):
    x: float
    y: float

    def shift_by(self, *, x: float = 0, y: float = 0):
        return Point(x=self.x + x, y=self.y + y)


class Line:
    _opts: SvgPitchGraphOptions
    start: Optional[Point]
    end: Optional[Point]

    def __init__(self, options: SvgPitchGraphOptions):
        self._opts = options
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

    def draw(self, trailing: bool = False) -> str:
        assert self.start is not None and self.end is not None
        stroke = "gray" if trailing else "black"
        return (
            f'<line stroke="{stroke}" stroke-width="{self._opts.stroke_width:.2f}" '
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
    _opts: SvgPitchGraphOptions
    _lines: list[Line]

    def __init__(self, options: SvgPitchGraphOptions):
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

    def push(self, pos: Point) -> "Path":
        if len(self._lines) == 0:
            self.start_at(pos)
        elif self.last.is_completed():
            assert self.last.end
            self.start_at(self.last.end)
            self.go_to(pos)
        else:
            self.go_to(pos)
        return self

    def draw(self, trailing: bool = False) -> str:
        opts = self._opts
        drawn: list[str] = []
        line: Line
        for line in filter(lambda _line: _line.is_completed(), self._lines):
            drawn.append(line.adjust_to_radius(opts.circle_radius).draw(trailing))
        return "".join(drawn)


class SvgPitchGraphMaker:
    def __init__(self, options: SvgPitchGraphOptions):
        self._opts = options

    def make_circle(self, pos: Point, trailing: bool = False) -> str:
        """
        Create a circle that is positioned where two lines touch.
        """
        fill = "none" if trailing else "black"
        stroke = "gray" if trailing else "black"
        return (
            f'<circle fill="{fill}" stroke="{stroke}" stroke-width="{self._opts.stroke_width:.2f}" '
            f'cx="{pos.x:.3f}" cy="{pos.y:.3f}" r="{self._opts.circle_radius:.2f}" />'
        )

    def make_devoiced_circle(self, mora: Mora, pos: Point) -> str:
        """
        Make a circle around the mora text to show that it's devoiced.
        """
        if len(mora.txt) == 1:
            pos = pos.shift_by(
                x=self._opts.font_size / 2 + self._opts.text_dx,
                y=self._opts.text_dx + math.ceil(self._opts.stroke_width),
            )
            return (
                f'<circle class="devoiced" fill="none" stroke="black" cx="{pos.x:.0f}" cy="{pos.y:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" r="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_disarray}" />'
            )
        else:
            pos = pos.shift_by(
                x=-self._opts.font_size - self._opts.devoiced_rectangle_padding,
                y=-self._opts.font_size - math.floor(self._opts.stroke_width),
            )
            width = self._opts.font_size * 2 + self._opts.devoiced_rectangle_padding * 2
            height = self._opts.devoiced_circle_radius * 2
            return (
                f'<rect class="devoiced" fill="none" stroke="black" x="{pos.x:.0f}" y="{pos.y:.0f}" '
                f'width="{width:.0f}" height="{height:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" rx="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_disarray}" />'
            )

    def make_text(self, mora: Mora, pos: Point, dx: int) -> str:
        """
        Create a text element with the mora inside.
        """
        tspan_dx = self._opts.tspan_dx
        quark = (
            f'<tspan{append_classname(mora.quark.flags)} fill="red" dx="{tspan_dx:.0f}">{mora.quark.txt}</tspan>'
            if mora.quark
            else ""
        )
        return (
            f'<text{append_classname(mora.flags)} fill="black" font-size="{self._opts.font_size}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{mora.txt}{quark}</text>'
        )

    def calc_svg_width(self, moras: list[Mora], pitch_type: PitchType) -> int:
        count = len(moras) + (1 if pitch_type == PitchType.heiban or len(moras) == 1 else 0)  # todo
        return count * self._opts.x_step + self._opts.graph_horizontal_padding * 2

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._opts.graph_font}" viewBox="0 0 {width} {height}" '
            f'height="{visible_height}px" xmlns="http://www.w3.org/2000/svg">{contents}</svg>'
        )

    def make_trailing_line(self, start: Point, end: Point) -> str:
        opts = self._opts
        # 1-mora heiban words start low, so the last mora is still low.
        trail_line = Path(opts).start_at(start).go_to(end).draw(trailing=True)
        trail_circle = self.make_circle(end, trailing=True)
        return make_group([trail_line, trail_circle], "trail")

    def make_graph(self, entry: FormattedEntry) -> str:
        opts = self._opts
        moras = entry_to_moras(entry)
        pitch_type = pitch_type_from_pitch_num(moras, entry.pitch_number)

        height_high = opts.size_unit
        height_low = height_high + opts.graph_height
        height_kana = height_low + opts.x_step
        pos = Point(opts.size_unit + opts.graph_horizontal_padding, opts.size_unit)

        word_circles: list[str] = []
        text_moras: list[str] = []
        path = Path(opts)

        for idx, mora in enumerate(moras):
            pos = Point(pos.x, height_high if mora.level == PitchLevel.high else height_low)
            word_circles.append(self.make_circle(pos))
            path.push(pos)

            if MoraFlag.devoiced in mora.flags:
                # circle around text
                text_moras.append(self.make_devoiced_circle(mora, Point(pos.x, height_kana)))

            text_moras.append(self.make_text(mora, Point(pos.x, height_kana), dx=int(opts.text_dx) * len(mora.txt)))

            pos = pos.shift_by(x=opts.x_step)

        content: list[str] = []

        if pitch_type == PitchType.heiban or len(moras) == 1:  # todo
            assert height_high == pos.y or len(moras) == 1, f"can't proceed: {entry}"
            content.append(
                self.make_trailing_line(
                    start=Point(pos.x - opts.x_step, pos.y),
                    end=Point(pos.x, height_low if pitch_type == PitchType.atamadaka else height_high),
                )
            )

        content.append(make_group([path.draw()], "paths"))
        content.append(make_group(word_circles, "circles"))

        svg_width = self.calc_svg_width(moras, pitch_type)
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
            make_group(content, pitch_type.name),
            width=svg_width,
            height=svg_height,
            visible_height=visible_height,
        )
