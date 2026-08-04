# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum


@enum.unique
class SvgGraphColorMode(enum.Enum):
    """How SVG graph colors are applied to rendered pitch graphs.

    black_and_white: no CSS is loaded; default role colors are baked into element attributes.
    css: class-based CSS rules style the graphs; element attributes carry default colors
         as fallbacks (presentation attributes have specificity 0, so CSS rules override them).
    svg_attributes: user-configured colors are baked into element attributes; no CSS is loaded.
    """

    black_and_white = enum.auto()
    css = enum.auto()
    svg_attributes = enum.auto()


@enum.unique
class SvgGraphClassName(enum.Enum):
    """CSS class names used to style pitch graph elements and look up their colors.

    Renderable Role member names in pitch_artist/pitch_graph.py must have a matching
    member here, because Section.class_name is resolved as SvgGraphClassName[role.name].
    Role.empty is excluded: empty sections are filtered out before rendering.
    """

    # Tokyo
    heiban = enum.auto()
    atamadaka = enum.auto()
    nakadaka = enum.auto()
    odaka = enum.auto()
    kifuku = enum.auto()
    unknown = enum.auto()
    # Keihan
    keihan_heiban = enum.auto()
    keihan_low_heiban = enum.auto()
    keihan_atamadaka = enum.auto()
    keihan_nakadaka = enum.auto()
    keihan_low_nakadaka = enum.auto()
    keihan_odaka = enum.auto()
    keihan_low_odaka = enum.auto()
    keihan_particle = enum.auto()
    keihan_setsubigo = enum.auto()
    # Special
    particle = enum.auto()
    setsubigo = enum.auto()
    connector = enum.auto()
    black = enum.auto()
    white = enum.auto()
    nasal = enum.auto()
