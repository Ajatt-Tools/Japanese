# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.file_ops import rm_file
from japanese.pitch_accents.acc_dict_mgr_2 import AccDictToSqliteWriter


@pytest.fixture(scope="class")
def tmp_sqlite3_db_path(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "db.sqlite"
    yield db_path
    rm_file(db_path)


@pytest.fixture(scope="class")
def tmp_upd_file(tmp_path_factory):
    upd_file = tmp_path_factory.mktemp("data") / "db.updated"
    yield upd_file
    rm_file(upd_file)


@pytest.fixture(scope="class")
def tmp_user_accents_file(tmp_path_factory):
    user_accents_file = tmp_path_factory.mktemp("data") / "user_accents_empty.tsv"
    yield user_accents_file
    rm_file(user_accents_file)
