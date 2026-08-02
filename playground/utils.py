# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import pathlib
from contextlib import contextmanager

from anki.utils import tmpfile
from aqt import mw

from japanese.config_view import JapaneseConfig
from japanese.helpers.file_ops import rm_file
from japanese.pitch_accents.consts import FORMATTED_ACCENTS_UPDATED

# Cache directory for the database used in the playground.
CACHE_DIR = pathlib.Path(__file__).parent / "cache"
PLAYGROUND_DB_PATH = CACHE_DIR / "playground_db.sqlite3"
# The playground's copy of the "pitch accents table is up to date" marker file.
# Kept in the playground cache so the real user_files marker is never touched.
PITCH_ACCENTS_UPDATED_FILE = CACHE_DIR / FORMATTED_ACCENTS_UPDATED.name

@contextmanager
def tmp_sqlite3_db_path():
    db_path = tmpfile(suffix=".sqlite3")
    print(f"tmp db path: {db_path}")
    try:
        yield pathlib.Path(db_path)
    finally:
        rm_file(db_path)


@contextmanager
def persistent_sqlite3_db_path():
    CACHE_DIR.mkdir(exist_ok=True)
    print(f"persistent db path: {PLAYGROUND_DB_PATH}")
    try:
        yield pathlib.Path(PLAYGROUND_DB_PATH)
    finally:
        pass


def default_config_json_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent / "japanese" / "config.json"


class NoAnkiConfigView(JapaneseConfig):
    """
    Loads the default config without starting Anki.
    """

    def _set_underlying_dicts(self) -> None:
        assert mw is None, "Anki shouldn't be running"
        with open(default_config_json_path(), encoding="utf-8") as f:
            self._default_config = self._config = json.load(f)

    def write_config(self) -> None:
        """Ignore writes during tests."""
        print("write requested. doing nothing. config contents:")
        print(json.dumps(self._config, indent=4, ensure_ascii=False))
