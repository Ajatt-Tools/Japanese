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


class FormattedEntryToSvgAdapter:
    """Adapter from dictionary pitch entries to the shared SVG graph renderer."""

    _renderer: SvgGraphRenderer
    _opts: SvgPitchGraphOptionsConfigView

    def __init__(self, options: SvgPitchGraphOptionsConfigView) -> None:
        self._opts = options
        self._renderer = SvgGraphRenderer(options)

    def _mora_to_graph_mora(self, mora: Mora) -> SvgGraphMora:
        """Convert a dictionary pitch mora to the generic SVG graph model."""
        return SvgGraphMora(
            text=assemble_txt_content(mora, reading_format=self._opts.reading_format, tspan_dx=self._opts.tspan_dx),
            level=mora.level,
            class_attr=append_class_name(mora.flags),
            dx_units=mora.dx_units(),
            flags=mora.render_flags(),
        )

    def _entry_to_graph(self, entry: FormattedEntry) -> SvgGraph:
        """Convert a dictionary pitch entry to a normalized SVG graph."""
        seq = entry_to_moras(entry)
        return SvgGraph(
            sections=[
                SvgGraphWord(
                    class_name=seq.class_name(),
                    moras=[self._mora_to_graph_mora(mora) for mora in seq.moras],
                    is_particle=False,
                    connect_to_previous=ConnectToPrevious.none,
                )
            ],
            outer_class_name=seq.class_name(),
        )

    def make_graph(self, entry: FormattedEntry) -> str:
        """Render a dictionary pitch entry as SVG markup."""
        return self._renderer.render_graph(self._entry_to_graph(entry))
