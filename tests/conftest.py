# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import pathlib

# Force Qt to run without a real display so widget tests work in headless CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from aqt.qt import QApplication

from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.helpers.file_ops import rm_file
from playground.utils import NoAnkiConfigView
from tests import DATA_DIR


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QApplication:
    """Ensure a QApplication exists for widget tests."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="class")
def tmp_sqlite3_db_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    db_path = tmp_path_factory.mktemp("data") / "db.sqlite3"
    yield db_path
    rm_file(db_path)


@pytest.fixture(scope="class")
def tmp_db_connection(
    tmp_sqlite3_db_path: pathlib.Path,
    tmp_upd_file: pathlib.Path,
    tmp_user_accents_file: pathlib.Path,
) -> Sqlite3Buddy:
    with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
        yield db


@pytest.fixture(scope="class")
def tmp_upd_file(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    upd_file = tmp_path_factory.mktemp("data") / "db.updated"
    yield upd_file
    rm_file(upd_file)


@pytest.fixture(scope="class")
def tmp_user_accents_file(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    user_accents_file = DATA_DIR / "test_user_accents.tsv"
    yield user_accents_file


@pytest.fixture(scope="session")
def no_anki_config() -> NoAnkiConfigView:
    config = NoAnkiConfigView()
    config.furigana["maximum_results"] = 1
    # substitute audio sources
    config["audio_sources"] = [
        {
            "enabled": True,
            "name": "TAAS-TEST",
            "url": str(DATA_DIR / "taas_index.json"),
        },
    ]
    return config
