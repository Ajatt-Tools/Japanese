# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from aqt.qt import *

from japanese.lookup_dialog import ViewPitchAccentsDialog
from japanese.mecab_controller import MecabController
from japanese.pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from japanese.pitch_accents.accent_lookup import AccentLookup
from playground.utils import PITCH_ACCENTS_UPDATED_FILE, NoAnkiConfigView, persistent_sqlite3_db_path

EXAMPLE_SENTENCE = "夕日の中伝説の大樹の下で睦み合う二人"


def main() -> None:
    """Launch the pitch accent lookup dialog with an example sentence.

    Uses a persistent playground database, populating it with the bundled
    pitch accent data on the first run (subsequent runs start fast).
    """
    with persistent_sqlite3_db_path() as db_path:
        cfg = NoAnkiConfigView()
        acc_dict = AccentDictManager2(
            db_path=db_path,
            upd_file_path=PITCH_ACCENTS_UPDATED_FILE,
        )
        acc_dict.ensure_dict_ready_on_main()
        accent_lookup = AccentLookup(cfg, MecabController(verbose=False, cache_max_size=cfg.cache_lookups))
        app = QApplication(sys.argv)
        dialog = ViewPitchAccentsDialog(cfg, accent_lookup=accent_lookup, accent_db_path=db_path)
        dialog.lookup_pronunciations(EXAMPLE_SENTENCE)
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
