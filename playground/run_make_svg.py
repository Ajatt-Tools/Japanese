# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.pitch_accents.colors import SvgGraphColorMode
from japanese.pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from playground.utils import NoAnkiConfigView
from tests.consts import DATA_DIR
from tests.test_make_svg import TEST_ENTRIES

SNAPSHOT_DIR = DATA_DIR / "formatted_entry_graphs"


def main() -> None:
    """Regenerate the dictionary-entry SVG snapshots compared by test_make_svg.

    The checked-in references are rendered in black-and-white mode,
    matching the override in tests/conftest.py.
    """
    config = NoAnkiConfigView()
    # Match the overrides in tests/conftest.py so references are byte-identical.
    config.svg_graphs["graph_font_name"] = "Noto Sans CJK JP"
    config.svg_graphs["color_mode"] = SvgGraphColorMode.black_and_white.name
    maker = FormattedEntryToSvgAdapter(config)
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    for idx, entry in enumerate(TEST_ENTRIES):
        with open(SNAPSHOT_DIR / f"test_{idx}.svg", "w", encoding="utf-8") as of:
            of.write(maker.make_graph(entry))


if __name__ == "__main__":
    main()
