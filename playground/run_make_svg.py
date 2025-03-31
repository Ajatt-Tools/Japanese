# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.config_view import SvgPitchGraphOptionsConfigView
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker
from playground.utils import NoAnkiConfigView
from tests import DATA_DIR
from tests.test_make_svg import TEST_ENTRIES


def main() -> None:
    config = NoAnkiConfigView()
    svg_config = SvgPitchGraphOptionsConfigView(config)
    maker = SvgPitchGraphMaker(options=svg_config)
    DATA_DIR.mkdir(exist_ok=True)
    for idx, entry in enumerate(TEST_ENTRIES):
        with open(DATA_DIR / f"test_{idx}.svg", "w", encoding="utf-8") as of:
            of.write(maker.make_graph(entry))


if __name__ == "__main__":
    main()
