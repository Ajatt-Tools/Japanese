# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker, SvgPitchGraphOptions
from tests.run_make_svg import TEST_ENTRIES, DATA_DIR


def test_make_svg() -> None:
    maker = SvgPitchGraphMaker(options=SvgPitchGraphOptions())
    for idx, entry in enumerate(TEST_ENTRIES):
        with open(DATA_DIR / f"test_{idx}.svg", encoding="utf-8") as f:
            assert f.read().strip() == maker.make_graph(entry).strip(), "generated content must match"
