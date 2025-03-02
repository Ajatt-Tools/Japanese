# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.file_ops import rm_file
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from japanese.pitch_accents.acc_dict_mgr_2 import AccDictToSqliteWriter


@pytest.fixture()
def tmp_sqlite3_buddy(tmpdir_factory):
    db_path = tmpdir_factory.mktemp("data").join("db.sqlite")
    yield Sqlite3Buddy(db_path=db_path)
    rm_file(db_path)


@pytest.fixture()
def tmp_acc_db_writer(tmpdir_factory):
    upd_file = tmpdir_factory.mktemp("data").join("db.updated")
    user_accents_file = tmpdir_factory.mktemp("data").join("user_accents_empty.tsv")
    yield lambda db: AccDictToSqliteWriter(
        db,
        upd_file=upd_file,
        user_accents_file=user_accents_file,
    )
    rm_file(upd_file)
    rm_file(user_accents_file)
