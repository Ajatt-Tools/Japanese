# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.helpers.file_ops import rm_file
from tests import DATA_DIR


@pytest.fixture(scope="class")
def tmp_sqlite3_db_path(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "db.sqlite3"
    yield db_path
    rm_file(db_path)


@pytest.fixture(scope="class")
def tmp_db_connection(tmp_sqlite3_db_path, tmp_upd_file, tmp_user_accents_file):
    with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
        yield db


@pytest.fixture(scope="class")
def tmp_upd_file(tmp_path_factory):
    upd_file = tmp_path_factory.mktemp("data") / "db.updated"
    yield upd_file
    rm_file(upd_file)


@pytest.fixture(scope="class")
def tmp_user_accents_file(tmp_path_factory):
    user_accents_file = DATA_DIR / "test_user_accents.tsv"
    yield user_accents_file
