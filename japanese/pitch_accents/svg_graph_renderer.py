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

    def make_devoiced_circle(self, pos: Point, multi_char: bool) -> str:
        """
        Create a dashed circle around devoiced mora text.
        If multi_char is true, widen the circle. This is needed if the mora consists of two characters.
        """
        if not multi_char:
            pos = pos.shift_by(
                x=self._opts.font_size / 2 + self._opts.text_dx,
                y=-self._opts.font_size / 2 + self._opts.devoiced_circle_dy,
            )
            return (
                f'<circle class="devoiced" fill="none" stroke="black" cx="{pos.x:.0f}" cy="{pos.y:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" r="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_dasharray}" />'
            )
        else:
            pos = pos.shift_by(
                x=-self._opts.font_size / 2 - self._opts.devoiced_rectangle_padding + self._opts.text_dx,
                y=-self._opts.font_size / 2 - self._opts.devoiced_circle_radius + self._opts.devoiced_circle_dy,
            )
            width = self._opts.font_size * 2 + self._opts.devoiced_rectangle_padding * 2
            height = self._opts.devoiced_circle_radius * 2
            return (
                f'<rect class="devoiced" fill="none" stroke="black" x="{pos.x:.0f}" y="{pos.y:.0f}" '
                f'width="{width:.0f}" height="{height:.0f}" '
                f'stroke-width="{self._opts.devoiced_circle_width:.2f}" rx="{self._opts.devoiced_circle_radius:.2f}" '
                f'stroke-dasharray="{self._opts.devoiced_stroke_dasharray}" />'
            )

    def make_text_element(self, text: str, pos: Point, class_attr: str, dx: int) -> str:
        """Create an SVG text element from preformatted text content and class attributes."""
        return (
            f'<text{class_attr} fill="black" '
            f'font-size="{self._opts.font_size:.1f}px" '
            f'letter-spacing="{self._opts.letter_spacing:.1f}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{text}</text>'
        )

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        """Wrap SVG child markup in the pitch graph SVG element."""
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._opts.graph_font_name}" '
            f'viewBox="0 0 {width} {height}" height="{visible_height}px" '
            f'xmlns="http://www.w3.org/2000/svg">{contents}</svg>'
        )
