# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import typing
from collections.abc import Iterable
from math import sqrt

from ..config_view import SvgPitchGraphOptionsConfigView
from .entry_to_moras import MoraFlag, mora_flags2class_name


@enum.unique
class SvgColor(enum.Enum):
    trail = "gray"
    word = "black"
    nasal = "red"


def make_group(elements: Iterable[str], class_name: str) -> str:
    attrs = f' class="{class_name}"' if class_name else ""
    return f'<g{attrs}>{"".join(elements)}</g>'


def append_class_name(mora_flag: MoraFlag) -> str:
    class_name = mora_flags2class_name(mora_flag)
    return f' class="{class_name}"' if class_name else ""


def attrs_circle(is_trailing: bool, is_particle: bool) -> str:
    if is_trailing:
        return f'class="{SvgColor.trail.name}" fill="none" stroke="{SvgColor.trail.value}"'
    if is_particle:
        return f'fill="none" stroke="{SvgColor.word.value}"'
    return f'fill="{SvgColor.word.value}" stroke="{SvgColor.word.value}"'


class Point(typing.NamedTuple):
    x: float
    y: float

    @classmethod
    def new(cls, x: int | float, y: int | float) -> "Point":
        return cls(x=float(x), y=float(y))

    def shift_by(self, *, x: int | float = 0.0, y: int | float = 0.0) -> "Point":
        return Point.new(x=self.x + x, y=self.y + y)

    def replace(self, *, x: int | float | None = None, y: int | float | None = None) -> "Point":
        return Point.new(x=x if x is not None else self.x, y=y if y is not None else self.y)


class Line:
    """An SVG line segment between two points, optionally rendered as a dashed (tape) line."""

    _opts: SvgPitchGraphOptionsConfigView
    is_trailing: bool
    start: Point | None
    end: Point | None
    _tape: bool

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self.is_trailing = False
        self.start = None
        self.end = None
        self._tape = False

    def start_at(self, pos: Point, tape: bool = False) -> "Line":
        self.start = pos
        self._tape = tape
        return self

    def end_at(self, pos: Point) -> "Line":
        self.end = pos
        return self

    def is_unfinished(self) -> bool:
        """Return True if the line has a start point but no end point."""
        return self.start is not None and self.end is None

    def is_completed(self) -> bool:
        """Return True if the line has both start and end points."""
        return self.start is not None and self.end is not None

    def draw(self) -> str:
        assert self.start is not None and self.end is not None
        attrs = []
        if self._tape:
            attrs.append(f'stroke-dasharray="{self._opts.stroke_dasharray}"')
        if self.is_trailing:
            attrs.append(f'class="{SvgColor.trail.name}"')
            attrs.append(f'stroke="{SvgColor.trail.value}"')
        else:
            attrs.append(f'stroke="{SvgColor.word.value}"')
        attrs.append(f'stroke-width="{self._opts.stroke_width:.2f}"')
        attrs.append(f'x1="{self.start.x:.3f}"')
        attrs.append(f'y1="{self.start.y:.3f}"')
        attrs.append(f'x2="{self.end.x:.3f}"')
        attrs.append(f'y2="{self.end.y:.3f}"')
        return f'<line {" ".join(attrs)} />'

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
        """Begin a new line segment at the given coordinates."""
        self._lines.append(Line(self._opts).start_at(pos))
        return self

    def go_to(self, pos: Point) -> "Path":
        """Set the end point of the current (last) line segment."""
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
        return "".join(
            line.adjust_to_radius(self._opts.circle_radius).draw() for line in self._lines if line.is_completed()
        )
