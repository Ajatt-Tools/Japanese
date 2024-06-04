# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from tests.no_anki_config import NoAnkiConfigView
from tests.run_make_svg import TEST_ENTRIES, DATA_DIR


def test_make_svg() -> None:
    config = NoAnkiConfigView()
    svg_config = SvgPitchGraphOptionsConfigView(config)
    maker = SvgPitchGraphMaker(options=svg_config)
    for idx, entry in enumerate(TEST_ENTRIES):
        with open(DATA_DIR / f"test_{idx}.svg", encoding="utf-8") as f:
            assert f.read().strip() == maker.make_graph(entry).strip(), "generated content must match"
