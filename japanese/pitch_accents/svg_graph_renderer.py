# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from config_view import SvgPitchGraphOptionsConfigView

from .svg_components import Point, attrs_circle


class SvgGraphRenderer:
    """Render normalized pitch graph data as SVG markup."""

    _opts: SvgPitchGraphOptionsConfigView

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options

    def make_circle(self, pos: Point, is_trailing: bool, is_particle: bool) -> str:
        """Create a circle positioned where two pitch lines touch."""
        return (
            f"<circle {attrs_circle(is_trailing=is_trailing, is_particle=is_particle)} "
            f'stroke-width="{self._opts.stroke_width:.2f}" '
            f'cx="{pos.x:.3f}" cy="{pos.y:.3f}" r="{self._opts.circle_radius:.2f}" />'
        )
