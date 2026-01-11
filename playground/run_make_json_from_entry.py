# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import shutil

from japanese.pitch_accents.entry_to_moras import entry_to_moras
from japanese.pitch_accents.pitch_to_json import mora_sequence_to_dict
from tests.test_make_svg import TEST_ENTRIES


def main() -> None:
    for idx, entry in enumerate(TEST_ENTRIES):
        seq = entry_to_moras(entry)
        d = mora_sequence_to_dict(seq)
        print(json.dumps(d, indent=4, ensure_ascii=False))
        print("=" * shutil.get_terminal_size()[0])


if __name__ == "__main__":
    main()
