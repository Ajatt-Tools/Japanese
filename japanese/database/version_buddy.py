# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from .basic_types import Sqlite3Buddy, Sqlite3BuddyVersionError, cursor_buddy

VERSION_TABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS version(
    schema_name     TEXT    primary key NOT NULL,
    number          INTEGER             NOT NULL
);
"""


class VersionSqlite3Buddy:
    """
    Manages versions of the table groups inside the database.
    """

    def prepare_version_table(self: Sqlite3Buddy) -> None:
        with cursor_buddy(self.con) as cur:
            cur.executescript(VERSION_TABLES_SCHEMA)
            self.con.commit()

    def get_db_version(self: Sqlite3Buddy, schema_name: str) -> int:
        query = """
        SELECT number FROM version
        WHERE schema_name = ?
        LIMIT 1 ;
        """
        cursor = self.con.execute(query, (schema_name,))
        result = cursor.fetchone()
        if result is None:
            raise Sqlite3BuddyVersionError("attempted to get version before setting it.")
        assert result[0] > 0, "expected positive integer"
        return result[0]

    def set_db_version(self: Sqlite3Buddy, schema_name: str, value: int) -> None:
        query = """
        INSERT INTO version (schema_name, number)
        VALUES (:schema_name, :number)
        ON CONFLICT(schema_name) DO UPDATE
            SET number = :number
            WHERE schema_name = :schema_name ;
        """
        self.con.execute(query, {"schema_name": schema_name, "number": value})
        self.con.commit()
