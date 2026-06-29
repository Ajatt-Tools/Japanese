# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import mw

from ..config_view import JapaneseConfig
from ..helpers.profiles import PitchOutputFormat
from .pitch_graph import Section, SvgPitchArtistGraphMaker, apply_kanji_colors


class PitchArtist:
    def __init__(self, cfg: JapaneseConfig) -> None:
        self._cfg = cfg
        self._gen = SvgPitchArtistGraphMaker(self._cfg)

    def generate(self, src_text: str, output_format: PitchOutputFormat) -> str:
        """Generate pitch graphs and colored text from the source field and write them to the note."""
        assert mw and mw.col, "Collection must be open."
        src_text = mw.col.media.strip(src_text).strip()
        if not src_text:
            return ""
        seq_sequences = self._gen.make_sequences(src_text)
        match output_format:
            case PitchOutputFormat.artist_svg:
                return self.generate_svg_graph(seq_sequences)
            case PitchOutputFormat.artist_colors:
                return self.generate_colored_text(seq_sequences)
            case _:
                raise ValueError(f"unsupported output format: {output_format.name}")

    def generate_svg_graph(self, seq_sequences: list[list[Section]]) -> str:
        sep_graphs = self._cfg.pitch_artist.separator_expression_graphs
        return sep_graphs.join(self._gen.make_graphs(seq_sequences))

    def generate_colored_text(self, seq_sequences: list[list[Section]]) -> str:
        sep_sent = self._cfg.pitch_artist.separator_sentences
        return sep_sent.join(apply_kanji_colors(seq_sequences))
