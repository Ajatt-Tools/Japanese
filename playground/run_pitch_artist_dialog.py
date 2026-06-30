# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from aqt.qt import *

from japanese.pitch_artist.artist_dialog import PitchArtistDialog
from playground.utils import NoAnkiConfigView


def main() -> None:
    app = QApplication(sys.argv)
    cfg = NoAnkiConfigView()
    form = PitchArtistDialog(cfg)
    form.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
