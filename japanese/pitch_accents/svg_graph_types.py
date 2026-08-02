# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import typing
from collections.abc import Sequence

from .colors import SvgGraphClassName


@enum.unique
class PitchLevel(enum.Enum):
    """Pitch height for a normalized SVG mora."""

    low = "l"
    high = "h"


@enum.unique
class SvgMoraFlag(enum.Flag):
    """Rendering flags for a normalized SVG mora."""

    nasal = enum.auto()
    trailing = enum.auto()  # trailing means it will be a gray line with a pierced circle
    devoiced = enum.auto()
    multi_char = enum.auto()
    text_hidden = enum.auto()


@enum.unique
class ConnectToPrevious(enum.Enum):
    """How a rendered section connects to the previous rendered section."""

    none = enum.auto()
    weld = enum.auto()
    tape = enum.auto()


class SvgGraphMora(typing.NamedTuple):
    """A single normalized mora ready for SVG rendering."""

    text: str
    level: PitchLevel
    class_attr: str = ""
    dx_units: int = 1
    flags: SvgMoraFlag = SvgMoraFlag(0)

    @property
    def is_trailing(self) -> bool:
        """Return True when this mora is a trailing placeholder circle."""
        if SvgMoraFlag.trailing in self.flags:
            assert len(self.text) == 0
            return True
        return False

    @property
    def is_multi_char(self) -> bool:
        """Return True when this mora is rendered as multiple kana characters."""
        return SvgMoraFlag.multi_char in self.flags

    @property
    def is_text_hidden(self) -> bool:
        """Return True when this mora should affect layout but not print text."""
        return SvgMoraFlag.text_hidden in self.flags


class SvgGraphWord(typing.NamedTuple):
    """A renderable group of morae."""

    class_name: SvgGraphClassName
    moras: Sequence[SvgGraphMora]
    is_particle: bool
    # Set by adapter code. Controls whether this section welds, tapes, or does not connect to the previous one.
    connect_to_previous: ConnectToPrevious

    @property
    def starts_with_trailing_mora(self) -> bool:
        """Return True if this section starts with a trailing marker mora."""
        return bool(self.moras and self.moras[0].is_trailing)


class SvgGraph(typing.NamedTuple):
    """A normalized pitch graph independent of the source notation domain."""

    sections: Sequence[SvgGraphWord]
    # When outer class name is not empty, the graph is being constructed from an instance of FormattedEntry.
    outer_class_name: SvgGraphClassName | None
