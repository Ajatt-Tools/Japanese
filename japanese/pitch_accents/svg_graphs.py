# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from ..config_view import SvgPitchGraphOptionsConfigView
from .common import FormattedEntry
from .entry_to_moras import Mora, entry_to_moras
from .svg_components import (
    append_class_name,
    assemble_txt_content,
)
from .svg_graph_renderer import SvgGraphRenderer
from .svg_graph_types import ConnectToPrevious, SvgGraph, SvgGraphMora, SvgGraphWord


class SvgPitchGraphMaker:
    """Adapter from dictionary pitch entries to the shared SVG graph renderer."""

    _renderer: SvgGraphRenderer
    _opts: SvgPitchGraphOptionsConfigView

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self._renderer = SvgGraphRenderer(options)

    def make_text(self, mora: Mora, pos: Point, dx: int) -> str:
        """
        Create a text element with the mora inside.
        """
        assert not mora.is_trailing()
        return self._renderer.make_text_element(self.assemble_txt_content(mora.txt), pos, append_class_name(mora.flags), dx)

    def calc_svg_width(self, moras: list[Mora]) -> int:
        return len(moras) * self._opts.x_step + self._opts.graph_horizontal_padding * 2

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
                text_moras.append(self._renderer.make_devoiced_circle(pos.replace(y=height_kana), extend=mora.is_multi_char()))

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
