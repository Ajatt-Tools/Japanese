# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc
import sqlite3
from contextlib import contextmanager


class Sqlite3BuddyABC(abc.ABC):
    con: sqlite3.Connection

    @abc.abstractmethod
    def get_db_version(self, schema_name: str) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def set_db_version(self, schema_name: str, value: int) -> None:
        raise NotImplementedError()


class Sqlite3BuddyError(RuntimeError):
    pass


class InvalidSourceIndex(Sqlite3BuddyError):
    pass


class Sqlite3BuddyVersionError(Sqlite3BuddyError):
    pass


@contextmanager
def cursor_buddy(connection: sqlite3.Connection):
    """
    Create, use, then clean up a temporary cursor.
    """
    cursor = connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
