# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import pathlib
from contextlib import contextmanager

from anki.utils import tmpfile
from aqt import mw

from japanese.config_view import JapaneseConfig
from japanese.helpers.file_ops import rm_file

# Cache directory for the database used in the playground.
CACHE_DIR = pathlib.Path(__file__).parent / "cache"


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
    db_path = CACHE_DIR / "playground_db.sqlite3"
    print(f"persistent db path: {db_path}")
    try:
        yield pathlib.Path(db_path)
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
        with open(default_config_json_path()) as f:
            self._default_config = self._config = json.load(f)
