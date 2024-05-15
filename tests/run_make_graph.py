# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.pitch_accents.common import FormattedEntry
from japanese.pitch_accents.svg_graphs import SvgPitchGraphMaker, SvgPitchGraphOptions


def main() -> None:
    entries = (
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
    )

    maker = SvgPitchGraphMaker(options=SvgPitchGraphOptions())

    for idx, entry in enumerate(entries):
        with open(f"test_{idx}.svg", "w", encoding="utf-8") as of:
            of.write(maker.make_graph(entry))


if __name__ == "__main__":
    main()
