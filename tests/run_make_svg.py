# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker, SvgPitchGraphOptions

DATA_DIR = pathlib.Path(__file__).parent / "data"
TEST_ENTRIES = (
    FormattedEntry(
        "ジンロウ",
        "<low_rise>ジ</low_rise><high>ンロウ</high>",
        "0",
    ),
    FormattedEntry(
        "スイソウガク",
        "<low_rise>ス</low_rise><high_drop>イソ</high_drop><low>ーカ<nasal>&#176;</nasal>ク</low>",
        "3",
    ),
    FormattedEntry(
        "ツケヒモ",
        "<low_rise><devoiced>ツ</devoiced></low_rise><high>ケヒモ</high>",
        "0",
    ),
)


def main() -> None:
    maker = SvgPitchGraphMaker(options=SvgPitchGraphOptions())
    DATA_DIR.mkdir(exist_ok=True)
    for idx, entry in enumerate(TEST_ENTRIES):
        with open(DATA_DIR / f"test_{idx}.svg", "w", encoding="utf-8") as of:
            of.write(maker.make_graph(entry))


if __name__ == "__main__":
    main()
