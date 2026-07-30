# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum


@enum.unique
class SvgGraphColorMode(enum.Enum):
    black_and_white = enum.auto()
    css = enum.auto()
    svg_attributes = enum.auto()
