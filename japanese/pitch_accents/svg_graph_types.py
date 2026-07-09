# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import typing
from collections.abc import Sequence

from .entry_to_moras import PitchLevel


@enum.unique
class SvgMoraFlag(enum.Flag):
    """Rendering flags for a normalized SVG mora."""

    trailing = enum.auto()
    devoiced = enum.auto()
    multi_char = enum.auto()
    text_hidden = enum.auto()


class SvgGraphMora(typing.NamedTuple):
    """A single normalized mora ready for SVG rendering."""

    text: str
    level: PitchLevel
    class_attr: str = ""
    dx_units: int = 1
    flags: SvgMoraFlag = SvgMoraFlag(0)


class SvgGraphSection(typing.NamedTuple):
    """A renderable group of morae and optional connection metadata."""

    class_name: str
    moras: Sequence[SvgGraphMora]
    is_particle: bool
    connect_to_previous: bool = False
    tape_connector: bool = False


class SvgGraph(typing.NamedTuple):
    """A normalized pitch graph independent of the source notation domain."""

    sections: Sequence[SvgGraphSection]
    outer_class_name: str = ""
    section_grouped: bool = False
