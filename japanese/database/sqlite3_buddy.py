# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
import sqlite3
from typing import Optional

from aqt import mw

from ..helpers.file_ops import user_files_dir
from .audio_buddy import AudioSqlite3Buddy
from .basic_types import Sqlite3BuddyError
from .pitch_buddy import PitchSqlite3Buddy
from .sqlite_schema import CURRENT_DB
from .version_buddy import VersionSqlite3Buddy

CURRENT_DB.remove_deprecated_files()


class Sqlite3Buddy(VersionSqlite3Buddy, AudioSqlite3Buddy, PitchSqlite3Buddy):
    """
    Tables for audio:  ('meta', 'headwords', 'files')
    Table for pitch accents: 'pitch_accents_formatted'
    """

    _db_path: pathlib.Path = pathlib.Path(user_files_dir()) / CURRENT_DB.name
    _con: Optional[sqlite3.Connection]

    def __init__(self, db_path: Optional[pathlib.Path] = None) -> None:
        if mw is None:
            # if running tests
            assert db_path, "db path should be set"
            assert db_path != self._db_path, "db path should not point to the user's database"
        self._db_path = db_path or self._db_path
        self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        assert self._con
        return self._con

    def can_execute(self) -> bool:
        return self._con is not None

    def start_session(self) -> None:
        if self.can_execute():
            raise Sqlite3BuddyError("connection is already created.")
        is_new_file = not self._db_path.is_file()
        self._con: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._con.row_factory = sqlite3.Row
        self._prepare_tables(is_new_file)

    def _prepare_tables(self, is_new_file: bool):
        self.prepare_version_table()
        self.prepare_audio_tables(is_new_file)
        self.prepare_pitch_accents_table(is_new_file)

    def end_session(self) -> None:
        if not self.can_execute():
            raise Sqlite3BuddyError("there is no connection to close.")
        self.con.commit()
        self.con.close()
        self._con = None

    def __enter__(self):
        """
        Create a temporary connection.
        Use when working in a different thread since the same connection can't be reused in another thread.
        """
        assert self._con is None
        self.start_session()
        assert self._con is not None
        self.con.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up a temporary connection.
        Use when working in a different thread since the same connection can't be reused in another thread.
        """
        # Call __exit__ of the connection instance.
        # If there was any exception, a rollback takes place. Otherwise, it commits.
        self.con.__exit__(exc_type, exc_val, exc_tb)
        self.end_session()
