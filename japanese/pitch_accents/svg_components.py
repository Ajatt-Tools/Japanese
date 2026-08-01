# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import typing
from collections.abc import Iterable
from math import sqrt

from ..config_view import JapaneseConfig, SvgGraphReadingFormat
from ..mecab_controller import to_hiragana, to_katakana
from .entry_to_moras import Mora, Quark, mora_flags2class_name
from .svg_graph_types import SvgMoraFlag


@enum.unique
class SvgColor(enum.Enum):
    """Named colors used by pitch graph SVG primitives."""

    trail = "gray"
    word = "black"
    nasal = "red"


def make_group(elements: Iterable[str], class_name: str) -> str:
    """Wrap SVG fragments in a group, optionally adding a CSS class."""
    attrs = f' class="{class_name}"' if class_name else ""
    return f'<g{attrs}>{"".join(elements)}</g>'


def append_class_name(mora_flag: SvgMoraFlag) -> str:
    """Return a class attribute for mora flags, or an empty string."""
    class_name = mora_flags2class_name(mora_flag)
    return f' class="{class_name}"' if class_name else ""


def attrs_circle(is_trailing: bool, is_particle: bool) -> str:
    """Return SVG circle attributes for pitch points."""
    if is_trailing:
        return f'class="{SvgColor.trail.name}" fill="none" stroke="{SvgColor.trail.value}"'
    if is_particle:
        return f'fill="none" stroke="{SvgColor.word.value}"'
    return f'fill="{SvgColor.word.value}" stroke="{SvgColor.word.value}"'


def quark_to_tspan(quark: Quark, tspan_dx: int | float) -> str:
    """Render a nasal or handakuten quark as a colored SVG tspan."""
    assert isinstance(quark, Quark)
    return (
        f'<tspan{append_class_name(quark.flags)} fill="{SvgColor.nasal.value}" dx="{tspan_dx:.0f}">{quark.txt}</tspan>'
    )


def mora_text_to_str(text: Quark | str, reading_format: SvgGraphReadingFormat, tspan_dx: int | float) -> str:
    """Convert a kana string according to the configured reading format."""
    if isinstance(text, Quark):
        return quark_to_tspan(text, tspan_dx=tspan_dx)
    assert isinstance(text, str), "text must be str"
    match reading_format:
        case SvgGraphReadingFormat.hiragana:
            return to_hiragana(text)
        case SvgGraphReadingFormat.katakana:
            return to_katakana(text)


def assemble_txt_content(mora: Mora, reading_format: SvgGraphReadingFormat, tspan_dx: int | float) -> str:
    """Assemble all text fragments for a mora into SVG text content."""
    return "".join(mora_text_to_str(txt, reading_format, tspan_dx) for txt in mora.txt)


class Point(typing.NamedTuple):
    """An SVG coordinate point."""

    x: float
    y: float

    @classmethod
    def new(cls, x: int | float, y: int | float) -> "Point":
        """Create a Point while normalizing coordinates to floats."""
        return cls(x=float(x), y=float(y))

    def shift_by(self, *, x: int | float = 0.0, y: int | float = 0.0) -> "Point":
        """Return a new point shifted by the given deltas."""
        return Point.new(x=self.x + x, y=self.y + y)

    def replace(self, *, x: int | float | None = None, y: int | float | None = None) -> "Point":
        """Return a new point with selected coordinates replaced."""
        return Point.new(x=x if x is not None else self.x, y=y if y is not None else self.y)


class Line:
    """An SVG line segment between two points, optionally rendered as a dashed (tape) line."""

    _cfg: JapaneseConfig
    is_trailing: bool
    start: Point | None
    end: Point | None
    _tape: bool

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Initialize an empty line with renderer options."""
        self._cfg = cfg
        self.is_trailing = False
        self.start = None
        self.end = None
        self._tape = False

    def start_at(self, pos: Point, tape: bool = False) -> "Line":
        """Set the line's start point and optional tape styling."""
        self.start = pos
        self._tape = tape
        return self

    def end_at(self, pos: Point) -> "Line":
        """Set the line's end point."""
        self.end = pos
        return self

    def is_unfinished(self) -> bool:
        """Return True if the line has a start point but no end point."""
        return self.start is not None and self.end is None

    def is_completed(self) -> bool:
        """Return True if the line has both start and end points."""
        return self.start is not None and self.end is not None

    def draw(self) -> str:
        """Render this completed line as SVG markup."""
        assert self.start is not None and self.end is not None
        attrs = []
        if self._tape:
            attrs.append(f'stroke-dasharray="{self._cfg.svg_graphs.stroke_dasharray}"')
        if self.is_trailing:
            attrs.append(f'class="{SvgColor.trail.name}"')
            attrs.append(f'stroke="{SvgColor.trail.value}"')
        else:
            attrs.append(f'stroke="{SvgColor.word.value}"')
        attrs.append(f'stroke-width="{self._cfg.svg_graphs.stroke_width:.2f}"')
        attrs.append(f'x1="{self.start.x:.3f}"')
        attrs.append(f'y1="{self.start.y:.3f}"')
        attrs.append(f'x2="{self.end.x:.3f}"')
        attrs.append(f'y2="{self.end.y:.3f}"')
        return f'<line {" ".join(attrs)} />'

    def adjust_to_radius(self, r: float) -> "Line":
        """Shorten this line so it touches circle edges instead of centers."""
        assert self.start is not None and self.end is not None

        opts = self._cfg.svg_graphs
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
    """A sequence of pitch-contour line segments."""

    _cfg: JapaneseConfig
    _lines: list[Line]

    def __init__(self, cfg: JapaneseConfig) -> None:
        """Initialize an empty pitch-contour path."""
        self._cfg = cfg
        self._lines = []

    @property
    def last(self) -> Line:
        """Return the last line segment in the path."""
        return self._lines[-1]

    def start_at(self, pos: Point) -> "Path":
        """Begin a new line segment at the given coordinates."""
        self._lines.append(Line(self._cfg).start_at(pos))
        return self

    def go_to(self, pos: Point) -> "Path":
        """Set the end point of the current (last) line segment."""
        self.last.end_at(pos)
        return self

    def push(self, pos: Point, is_trailing: bool) -> "Path":
        """Append a pitch point and mark the resulting segment as trailing when needed."""
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
        """Render all completed path segments as SVG line markup."""
        return "".join(
            line.adjust_to_radius(self._cfg.svg_graphs.circle_radius).draw()
            for line in self._lines
            if line.is_completed()
        )
