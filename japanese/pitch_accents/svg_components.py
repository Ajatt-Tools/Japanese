# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import typing
from collections.abc import Iterable
from math import sqrt

from ..config_view import JapaneseConfig, SvgGraphReadingFormat
from ..mecab_controller import to_hiragana, to_katakana
from .colors import SvgGraphClassName, SvgGraphColorMode
from .entry_to_moras import Mora, Quark, mora_flags2class_name
from .svg_graph_types import SvgMoraFlag


@enum.unique
class SvgBlackAndWhiteRole(enum.Enum):
    """Named colors used by pitch graph SVG primitives."""

    trail = "gray"
    word = "black"
    nasal = "red"


def make_group(elements: Iterable[str], class_name: str) -> str:
    """Wrap SVG fragments in a group, returning an empty string for empty content."""
    if not (content := "".join(elements)):
        return ""
    attrs = f' class="{class_name}"' if class_name else ""
    return f"<g{attrs}>{content}</g>"


def append_class_name(mora_flag: SvgMoraFlag) -> str:
    """Return a class attribute for mora flags, or an empty string."""
    class_name = mora_flags2class_name(mora_flag)
    return f' class="{class_name}"' if class_name else ""


def quark_to_tspan(quark: Quark, tspan_dx: int | float, nasal_color: str) -> str:
    """Render a nasal or handakuten quark as a colored SVG tspan."""
    assert isinstance(quark, Quark)
    # Keep fill as a presentation-attribute fallback for standalone/old SVGs.
    # In CSS color mode, loaded CSS rules override presentation attributes.
    return f'<tspan{append_class_name(quark.flags)} fill="{nasal_color}" dx="{tspan_dx:.0f}">{quark.txt}</tspan>'


def mora_text_to_str(
    text: Quark | str, reading_format: SvgGraphReadingFormat, tspan_dx: int | float, nasal_color: str
) -> str:
    """Convert a kana string according to the configured reading format."""
    if isinstance(text, Quark):
        return quark_to_tspan(text, tspan_dx=tspan_dx, nasal_color=nasal_color)
    assert isinstance(text, str), "text must be str"
    match reading_format:
        case SvgGraphReadingFormat.hiragana:
            return to_hiragana(text)
        case SvgGraphReadingFormat.katakana:
            return to_katakana(text)


def assemble_txt_content(
    mora: Mora, reading_format: SvgGraphReadingFormat, tspan_dx: int | float, nasal_color: str
) -> str:
    """Assemble all text fragments for a mora into SVG text content."""
    return "".join(mora_text_to_str(txt, reading_format, tspan_dx, nasal_color) for txt in mora.txt)


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


def lookup_component_color(cfg: JapaneseConfig, role: SvgBlackAndWhiteRole, class_name: SvgGraphClassName) -> str:
    """Resolve an SVG graph role class to its presentation-attribute fallback color.

    In CSS mode, these values remain in the SVG for backwards compatibility and
    standalone viewing. CSS rules override SVG presentation attributes, so the
    class-based stylesheet still controls colors when it is loaded.
    """
    match cfg.svg_graphs.color_mode:
        case SvgGraphColorMode.svg_attributes:
            return cfg.svg_graph_colors.lookup_color(class_name)
        case _:
            return role.value


def trail_color(cfg: JapaneseConfig) -> str:
    """Resolve the color used for trailing lines and circles (odaka drop markers)."""
    return lookup_component_color(cfg, SvgBlackAndWhiteRole.trail, SvgGraphClassName.connector)


class Line:
    """An SVG line segment between two points, optionally rendered as a dashed (tape) line."""

    _start: Point | None
    _end: Point | None

    _cfg: JapaneseConfig
    _is_trailing: bool
    _is_tape: bool

    def __init__(self, cfg: JapaneseConfig, class_name: SvgGraphClassName) -> None:
        """Initialize an empty line whose stroke color resolves from the given graph class."""
        self._cfg = cfg
        # Positions
        self._start = None
        self._end = None
        # Properties
        self._is_tape = False
        self._is_trailing = False
        self._class_name = class_name

    @property
    def end_point(self) -> Point:
        """Return the line's end point, raising ValueError if it is not set."""
        if self._end:
            return self._end
        raise ValueError("End is not set.")

    @property
    def is_trailing(self) -> bool:
        """Return True if this line uses trailing-mora styling."""
        return self._is_trailing

    def set_trailing(self, is_trailing: bool) -> "Line":
        """Set trailing styling and return self for chaining."""
        self._is_trailing = is_trailing
        return self

    def start_at(self, pos: Point, tape: bool = False) -> "Line":
        """Set the line's start point and optional tape styling."""
        self._start = pos
        self._is_tape = tape
        return self

    def end_at(self, pos: Point) -> "Line":
        """Set the line's end point."""
        self._end = pos
        return self

    def is_unfinished(self) -> bool:
        """Return True if the line has a start point but no end point."""
        return self._start is not None and self._end is None

    def is_completed(self) -> bool:
        """Return True if the line has both start and end points."""
        return self._start is not None and self._end is not None

    def draw(self) -> str:
        """Render this completed line as SVG markup."""
        assert self._start is not None and self._end is not None
        attrs: list[str] = []
        if self._is_tape:
            attrs.append(f'stroke-dasharray="{self._cfg.svg_graphs.stroke_dasharray}"')
        if self._is_trailing:
            attrs.append(f'class="{SvgBlackAndWhiteRole.trail.name}"')
            attrs.append(f'stroke="{trail_color(self._cfg)}"')
        else:
            stroke_color = lookup_component_color(self._cfg, SvgBlackAndWhiteRole.word, self._class_name)
            attrs.append(f'stroke="{stroke_color}"')
        attrs.append(f'stroke-width="{self._cfg.svg_graphs.stroke_width:.2f}"')
        attrs.append(f'x1="{self._start.x:.3f}"')
        attrs.append(f'y1="{self._start.y:.3f}"')
        attrs.append(f'x2="{self._end.x:.3f}"')
        attrs.append(f'y2="{self._end.y:.3f}"')
        return f'<line {" ".join(attrs)} />'

    def adjust_to_radius(self) -> "Line":
        """Shorten this line so it touches circle edges instead of centers."""
        assert self._start is not None and self._end is not None

        r = self._cfg.svg_graphs.circle_radius
        opts = self._cfg.svg_graphs
        tan = opts.graph_height / opts.x_step
        sin = tan / sqrt(1 + tan * tan)
        cos = 1 / sqrt(1 + tan * tan)

        offset_y = r * sin
        offset_x = r * cos

        if self._start.y == self._end.y:
            self._start = self._start.shift_by(x=r)
            self._end = self._end.shift_by(x=-r)
        elif self._start.y > self._end.y:
            self._start = self._start.shift_by(x=offset_x, y=-offset_y)
            self._end = self._end.shift_by(x=-offset_x, y=offset_y)
        elif self._start.y < self._end.y:
            self._start = self._start.shift_by(x=offset_x, y=offset_y)
            self._end = self._end.shift_by(x=-offset_x, y=-offset_y)

        return self


class Path:
    """A sequence of pitch-contour line segments."""

    _cfg: JapaneseConfig
    _lines: list[Line]

    def __init__(self, cfg: JapaneseConfig, class_name: SvgGraphClassName) -> None:
        """Initialize an empty pitch-contour path."""
        self._cfg = cfg
        self._lines = []
        self._class_name = class_name

    @property
    def last(self) -> Line:
        """Return the last line segment in the path."""
        return self._lines[-1]

    def start_at(self, pos: Point) -> "Path":
        """Begin a new line segment at the given coordinates."""
        self._lines.append(Line(self._cfg, self._class_name).start_at(pos))
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
            self.start_at(self.last.end_point)
            self.go_to(pos)
        else:
            self.go_to(pos)
        self.last.set_trailing(is_trailing)
        return self

    def draw(self) -> str:
        """Render all completed path segments as SVG line markup."""
        return "".join(line.adjust_to_radius().draw() for line in self._lines if line.is_completed())
