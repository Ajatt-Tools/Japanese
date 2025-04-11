# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import abc
import os
import typing
from collections.abc import Iterable, Sequence
from typing import Optional

from ..audio_manager.basic_types import AudioStats, NameUrl
from ..helpers.audio_json_schema import FileInfo, SourceIndex
from .basic_types import (
    InvalidSourceIndex,
    Sqlite3BuddyABC,
    Sqlite3BuddyVersionError,
    cursor_buddy,
)

NoneType = type(None)  # fix for the official binary bundle
MIN_SOURCE_VERSION = 2


class BoundFile(typing.NamedTuple):
    """
    Represents an sqlite query result.
    """

    headword: str
    file_name: str
    source_name: str

    def ext(self) -> str:
        return os.path.splitext(self.file_name)[-1]


def build_or_clause(repeated_field_name: str, count: int) -> str:
    return " OR ".join(f"{repeated_field_name} = ?" for _idx in range(count))


def raise_if_invalid_json(data: SourceIndex):
    """
    Validate index schema.
    Raise if format is not supported.
    """
    for field_name in SourceIndex.__annotations__:
        if field_name not in data:
            raise InvalidSourceIndex(f"audio source file is missing a required key: '{field_name}'")
    try:
        version = int(data["meta"]["version"])
    except (KeyError, ValueError):
        raise InvalidSourceIndex(f"Audio source index version not found.")

    if version < MIN_SOURCE_VERSION:
        raise InvalidSourceIndex(f"Outdated index schema: {version}. Minimum supported version: {MIN_SOURCE_VERSION}")


AUDIO_TABLES_SCHEMA: typing.Final[str] = """
--- Note: `source_name` is the name given to the audio source by the user,
--- and it can be arbitrary (e.g. NHK-2016).
--- `dictionary_name` is the name given to the audio source by its creator.
--- E.g. the NHK audio source provided by Ajatt-Tools has `dictionary_name` set to "NHK日本語発音アクセント新辞典".

CREATE TABLE IF NOT EXISTS meta(
    source_name     TEXT primary key NOT NULL,
    dictionary_name TEXT             NOT NULL,
    year            INTEGER          NOT NULL,
    version         INTEGER          NOT NULL,
    original_url    TEXT,
    media_dir       TEXT             NOT NULL,
    media_dir_abs   TEXT
);

CREATE TABLE IF NOT EXISTS headwords(
    source_name TEXT NOT NULL,
    headword    TEXT NOT NULL,
    file_name   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files(
    source_name   TEXT NOT NULL,
    file_name     TEXT NOT NULL,
    kana_reading  TEXT NOT NULL,
    pitch_pattern TEXT,
    pitch_number  TEXT
);

CREATE INDEX IF NOT EXISTS index_names ON meta(source_name);
CREATE INDEX IF NOT EXISTS index_file_names ON headwords(source_name, headword);
CREATE INDEX IF NOT EXISTS index_file_info ON files(source_name, file_name);
"""
AUDIO_TABLES_SCHEMA_VERSION: typing.Final[int] = 1
AUDIO_TABLES_SCHEMA_NAME: typing.Final[str] = "audio"


class AudioSqlite3Buddy(Sqlite3BuddyABC, abc.ABC):
    def prepare_audio_tables(self, is_new_file: bool) -> None:
        """
        Create sqlite3 tables and indexes if needed.
        If the db schema changes in the future, update the existing db.
        """
        with cursor_buddy(self.con) as cur:
            # Run the script to create tables and indexes if they don't exist.
            cur.executescript(AUDIO_TABLES_SCHEMA)
            self.con.commit()
        if not is_new_file:
            # The database file was created before.
            # Migrate the database if necessary.
            self._migrate_audio_db()
        self.set_db_version(AUDIO_TABLES_SCHEMA_NAME, AUDIO_TABLES_SCHEMA_VERSION)

    def _migrate_audio_db(self) -> None:
        """
        Check db version. Perform migrations if the version is old.
        """
        version = self.get_db_version(AUDIO_TABLES_SCHEMA_NAME)
        if version == AUDIO_TABLES_SCHEMA_VERSION:
            return
        if version is None:
            # version hasn't been set before = upgraded from an older version of the add-on.
            version = 1
        if version == 1:
            # Example:
            # query = """
            #   ALTER TABLE ...
            # """
            # self.con.executescript(query)
            # version += 1
            pass
        if version != AUDIO_TABLES_SCHEMA_VERSION:
            raise Sqlite3BuddyVersionError(
                f"After migration, version should be {AUDIO_TABLES_SCHEMA_VERSION}, but got {version}"
            )
        self.con.commit()

    def search_files_in_source(self, source_name: str, headword: str) -> Iterable[BoundFile]:
        query = """
        SELECT file_name FROM headwords
        WHERE source_name = ? AND headword = ?;
        """
        with cursor_buddy(self.con) as cur:
            results = cur.execute(query, (source_name, headword)).fetchall()
            assert type(results) is list
            return (
                BoundFile(file_name=result_tup["file_name"], source_name=source_name, headword=headword)
                for result_tup in results
            )

    def search_files(self, headword: str) -> Iterable[BoundFile]:
        query = """
        SELECT file_name, source_name FROM headwords
        WHERE headword = ?;
        """
        with cursor_buddy(self.con) as cur:
            results = cur.execute(query, (headword,)).fetchall()
            assert type(results) is list
            return (
                BoundFile(file_name=result_tup["file_name"], source_name=result_tup["source_name"], headword=headword)
                for result_tup in results
            )

    def get_file_info(self, source_name: str, file_name: str) -> FileInfo:
        query = """
        SELECT kana_reading, pitch_pattern, pitch_number FROM files
        WHERE source_name = ? AND file_name = ?
        LIMIT 1;
        """
        with cursor_buddy(self.con) as cur:
            result = cur.execute(query, (source_name, file_name)).fetchone()
            assert len(result) == 3 and all((type(val) in (str, NoneType)) for val in result)
            return {
                "kana_reading": result["kana_reading"],
                "pitch_pattern": result["pitch_pattern"],
                "pitch_number": result["pitch_number"],
            }

    def remove_data(self, source_name: str) -> None:
        """
        Remove all info about audio source from the database.
        """
        queries = (
            """ DELETE FROM meta      WHERE source_name = ?; """,
            """ DELETE FROM headwords WHERE source_name = ?; """,
            """ DELETE FROM files     WHERE source_name = ?; """,
        )
        with cursor_buddy(self.con) as cur:
            for query in queries:
                cur.execute(query, (source_name,))
            self.con.commit()

    def distinct_file_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        # Filenames in different audio sources may collide,
        # although it's not likely with the currently released audio sources.
        # To resolve collisions when counting distinct filenames,
        # dictionary_name and original_url are also taken into account.
        query = """
        SELECT COUNT(*) FROM (
            SELECT DISTINCT f.file_name, m.dictionary_name, m.original_url
            FROM files f
            INNER JOIN meta m ON f.source_name = m.source_name
            WHERE %s
        );
        """
        with cursor_buddy(self.con) as cur:
            result = cur.execute(
                query % build_or_clause("f.source_name", len(source_names)),
                source_names,
            ).fetchone()
            assert len(result) == 1
            return result[0]

    def distinct_headword_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        query = """
        SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords WHERE %s);
        """
        with cursor_buddy(self.con) as cur:
            # Return the number of unique headwords in the specified sources.
            result = cur.execute(
                query % build_or_clause("source_name", len(source_names)),
                source_names,
            ).fetchone()
            assert len(result) == 1
            return result[0]

    def get_stats_by_name(self, source: NameUrl) -> Optional[AudioStats]:
        query = """
        SELECT
            (SELECT COUNT(DISTINCT headword)  FROM headwords WHERE source_name = m.source_name) AS num_headwords,
            (SELECT COUNT(DISTINCT file_name) FROM files     WHERE source_name = m.source_name) AS num_files
        FROM meta m
        WHERE m.source_name = ? AND m.original_url = ? ;
        """
        with cursor_buddy(self.con) as cur:
            row = cur.execute(query, (source.name, source.url)).fetchone()
            if row is None:
                return None
            return AudioStats(source_name=source.name, num_headwords=row["num_headwords"], num_files=row["num_files"])

    def source_names(self) -> list[str]:
        with cursor_buddy(self.con) as cur:
            query_result = cur.execute(""" SELECT source_name FROM meta; """).fetchall()
            return [result_tuple[0] for result_tuple in query_result]

    def get_cached_sources(self) -> list[NameUrl]:
        query = """
        SELECT m.source_name, m.original_url
        FROM meta m
        WHERE EXISTS (
            SELECT 1 FROM headwords
            WHERE source_name = m.source_name
            LIMIT 1
        )
        AND EXISTS (
            SELECT 1 FROM files
            WHERE source_name = m.source_name
            LIMIT 1
        );
        """
        with cursor_buddy(self.con) as cur:
            rows = cur.execute(query).fetchall()
            return [NameUrl(row["source_name"], row["original_url"]) for row in rows]

    def clear_all_audio_data(self) -> None:
        """
        Remove all info about audio sources from the database.
        """
        queries = """
        DELETE FROM meta ;
        DELETE FROM headwords ;
        DELETE FROM files ;
        """
        with cursor_buddy(self.con) as cur:
            cur.executescript(queries)
            self.con.commit()

    def get_media_dir_abs(self, source_name: str) -> Optional[str]:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT media_dir_abs FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert len(result) == 1 and (type(result["media_dir_abs"]) in (str, NoneType))
            return result["media_dir_abs"]

    def get_media_dir_rel(self, source_name: str) -> str:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT media_dir FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert len(result) == 1 and type(result["media_dir"]) is str
            return result["media_dir"]

    def get_original_url(self, source_name: str) -> Optional[str]:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT original_url FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert len(result) == 1 and (type(result["original_url"]) in (str, NoneType))
            return result["original_url"]

    def set_original_url(self, source_name: str, new_url: str) -> None:
        with cursor_buddy(self.con) as cur:
            query = """ UPDATE meta SET original_url = ? WHERE source_name = ?; """
            cur.execute(query, (new_url, source_name))
            self.con.commit()

    def is_source_cached(self, source_name: str) -> bool:
        """True if audio source with this name has been cached already."""
        with cursor_buddy(self.con) as cur:
            queries = (
                """ SELECT 1 FROM meta      WHERE source_name = ? LIMIT 1; """,
                """ SELECT 1 FROM headwords WHERE source_name = ? LIMIT 1; """,
                """ SELECT 1 FROM files     WHERE source_name = ? LIMIT 1; """,
            )
            results = [cur.execute(query, (source_name,)).fetchone() for query in queries]
            return all(result is not None for result in results)

    def get_source_by_name(self, source_name: str) -> Optional[NameUrl]:
        query = """
        SELECT m.source_name, m.original_url
        FROM meta m
        WHERE m.source_name = ?
        AND EXISTS (
            SELECT 1 FROM headwords
            WHERE source_name = m.source_name
            LIMIT 1
        )
        AND EXISTS (
            SELECT 1 FROM files
            WHERE source_name = m.source_name
            LIMIT 1
        );
        """
        with cursor_buddy(self.con) as cur:
            result = cur.execute(query, (source_name,)).fetchone()
            assert result is None or type(result["source_name"]) is str
            return NameUrl(result["source_name"], result["original_url"]) if result else None

    def insert_data(self, source_name: str, data: SourceIndex):
        raise_if_invalid_json(data)
        with cursor_buddy(self.con) as cur:
            query = """
            INSERT INTO meta
            (source_name, dictionary_name, year, version, original_url, media_dir, media_dir_abs)
            VALUES(?, ?, ?, ?, ?, ?, ?);
            """
            # Insert meta.
            try:
                cur.execute(
                    query,
                    (
                        source_name,
                        data["meta"]["name"],
                        data["meta"]["year"],
                        data["meta"]["version"],
                        None,  # original URL can be null
                        data["meta"]["media_dir"],
                        data["meta"].get("media_dir_abs"),  # Possibly unset
                    ),
                )
            except KeyError as ex:
                raise InvalidSourceIndex(f"Missing field '{ex}'")
            # Insert headwords and file names
            query = """
            INSERT INTO headwords
            ( source_name, headword, file_name )
            VALUES( :source_name, :headword, :file_name );
            """
            cur.executemany(
                query,
                (
                    dict(source_name=source_name, headword=headword, file_name=file_name)
                    for headword, file_list in data["headwords"].items()
                    for file_name in file_list
                ),
            )
            # Insert readings and accent info.
            query = """
            INSERT INTO files
            ( source_name, file_name, kana_reading, pitch_pattern, pitch_number )
            VALUES( :source_name, :file_name, :kana_reading, :pitch_pattern, :pitch_number );
            """
            try:
                cur.executemany(
                    query,
                    (
                        dict(
                            source_name=source_name,
                            file_name=file_name,
                            kana_reading=file_info["kana_reading"],
                            pitch_pattern=file_info.get("pitch_pattern"),
                            pitch_number=file_info.get("pitch_number"),
                        )
                        for file_name, file_info in data["files"].items()
                    ),
                )
            except KeyError as ex:
                raise InvalidSourceIndex(f"Missing field '{ex}'")
            self.con.commit()
