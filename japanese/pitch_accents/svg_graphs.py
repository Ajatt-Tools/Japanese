# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from ..config_view import SvgGraphReadingFormat, SvgPitchGraphOptionsConfigView
from ..mecab_controller import to_katakana
from ..mecab_controller.kana_conv import to_hiragana
from .common import FormattedEntry
from .entry_to_moras import (
    Mora,
    MoraFlag,
    PitchLevel,
    Quark,
    entry_to_moras,
)
from .svg_components import (
    Path,
    Point,
    SvgColor,
    append_class_name,
    make_group,
)
from .svg_graph_renderer import SvgGraphRenderer


class SvgPitchGraphMaker:
    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self._renderer = SvgGraphRenderer(options)

    def make_devoiced_circle(self, pos: Point, extend: bool) -> str:
        """
        Make a circle around the mora text to show that it's devoiced.
        If extend is true, widen the circle. This is needed if the mora consists of two characters.
        """
        if not extend:
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

    def _quark_to_tspan(self, quark: Quark) -> str:
        assert isinstance(quark, Quark)
        return (
            f'<tspan{append_class_name(quark.flags)} fill="{SvgColor.nasal.value}" '
            f'dx="{self._opts.tspan_dx:.0f}">{quark.txt}</tspan>'
        )

    def _convert_kana(self, text: Quark | str, reading_format: SvgGraphReadingFormat) -> str:
        """Convert a kana string according to the configured reading format."""
        if not isinstance(text, str):
            return self._quark_to_tspan(text)
        assert isinstance(text, str)
        match reading_format:
            case SvgGraphReadingFormat.hiragana:
                return to_hiragana(text)
            case SvgGraphReadingFormat.katakana:
                return to_katakana(text)

    def assemble_txt_content(self, mora_txt: list[Quark | str]) -> str:
        return "".join(self._convert_kana(txt, self._opts.reading_format) for txt in mora_txt)

    def make_text_element(self, text: str, pos: Point, class_name: str, dx: int) -> str:
        """Create a text element from preformatted text content and CSS classes."""
        return (
            f'<text{class_name} fill="black" '
            f'font-size="{self._opts.font_size:.1f}px" '
            f'letter-spacing="{self._opts.letter_spacing:.1f}px" '
            f'x="{pos.x:.0f}" y="{pos.y:.0f}" dx="{dx:.0f}">{text}</text>'
        )

    def make_text(self, mora: Mora, pos: Point, dx: int) -> str:
        """
        Create a text element with the mora inside.
        """
        assert not mora.is_trailing()
        return self.make_text_element(self.assemble_txt_content(mora.txt), pos, append_class_name(mora.flags), dx)

    def calc_svg_width(self, moras: list[Mora]) -> int:
        return len(moras) * self._opts.x_step + self._opts.graph_horizontal_padding * 2

    def make_svg(self, contents: str, *, width: int, height: int, visible_height: int) -> str:
        return (
            f'<svg class="ajt__pitch_svg" style="font-family: {self._opts.graph_font_name}" viewBox="0 0 {width}'
            f' {height}" height="{visible_height}px" xmlns="http://www.w3.org/2000/svg">{contents}</svg>'
        )

    def calc_text_dx(self, mora: Mora) -> int:
        return int(self._opts.text_dx) * sum(1 for char in mora.txt if isinstance(char, str))

    def make_graph(self, entry: FormattedEntry) -> str:
        opts = self._opts
        seq = entry_to_moras(entry)

        height_high = opts.size_unit
        height_low = height_high + opts.graph_height
        height_kana = height_low + opts.x_step
        pos = Point.new(x=opts.size_unit + opts.graph_horizontal_padding, y=opts.size_unit)

        word_circles: list[str] = []
        text_moras: list[str] = []
        path = Path(opts)

        for idx, mora in enumerate(seq.moras):
            pos = pos.replace(y=height_high if mora.level == PitchLevel.high else height_low)
            word_circles.append(self._renderer.make_circle(pos, is_trailing=mora.is_trailing()))
            path.push(pos, is_trailing=mora.is_trailing())

            if MoraFlag.devoiced in mora.flags:
                # circle around text
                text_moras.append(self.make_devoiced_circle(pos.replace(y=height_kana), extend=mora.is_multi_char()))

            if not mora.is_trailing():
                text_moras.append(self.make_text(mora, pos.replace(y=height_kana), dx=self.calc_text_dx(mora)))

            pos = pos.shift_by(x=opts.x_step)

        content: list[str] = [
            make_group([path.draw()], "lines"),
            make_group(word_circles, "circles"),
        ]

        svg_width = self.calc_svg_width(seq.moras)
        svg_height_with_text = height_kana + opts.size_unit

        if opts.include_text:
            svg_height = svg_height_with_text
            visible_height = opts.graph_visible_height
            content.append(make_group(text_moras, "text"))
        else:
            svg_height = height_low + opts.size_unit
            ratio = svg_height / svg_height_with_text
            visible_height = int(ratio * opts.graph_visible_height)

        return self.make_svg(
            make_group(content, seq.pitch_type.name),
            width=svg_width,
            height=svg_height,
            visible_height=visible_height,
        )
