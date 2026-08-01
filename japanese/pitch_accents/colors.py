# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum


@enum.unique
class SvgGraphColorMode(enum.Enum):
    black_and_white = enum.auto()
    css = enum.auto()
    svg_attributes = enum.auto()


@enum.unique
class SvgGraphClassName(enum.Enum):
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
