# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib
import sqlite3
import typing
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from typing import Optional

from ..pitch_accents.common import AccDictRawTSVEntry
from .audio_json_schema import FileInfo, SourceIndex
from .file_ops import user_files_dir
from .sqlite_schema import CURRENT_DB

NoneType = type(None)  # fix for the official binary bundle

CURRENT_DB.remove_deprecated_files()


class BoundFile(typing.NamedTuple):
    """
    Represents an sqlite query result.
    """

    headword: str
    file_name: str
    source_name: str


def build_or_clause(repeated_field_name: str, count: int) -> str:
    return " OR ".join(f"{repeated_field_name} = ?" for _idx in range(count))


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


class Sqlite3BuddyError(RuntimeError):
    pass


class InvalidSourceIndex(Sqlite3BuddyError):
    pass


def raise_if_invalid_json(data: SourceIndex):
    for field_name in SourceIndex.__annotations__:
        if field_name not in data:
            raise InvalidSourceIndex(f"audio source file is missing a required key: '{field_name}'")


class Sqlite3Buddy:
    """
    Tables for audio:  ('meta', 'headwords', 'files')
    Table for pitch accents: 'pitch_accents_formatted'
    """

    _db_path: pathlib.Path = pathlib.Path(user_files_dir()) / CURRENT_DB.name
    _con: Optional[sqlite3.Connection]

    def __init__(self, db_path: Optional[pathlib.Path] = None) -> None:
        self._db_path = db_path or self._db_path
        self._con = None

    def can_execute(self) -> bool:
        return self._con is not None

    def start_session(self) -> None:
        if self.can_execute():
            raise Sqlite3BuddyError("connection is already created.")
        self._con: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._prepare_tables()

    def end_session(self) -> None:
        if not self.can_execute():
            raise Sqlite3BuddyError("there is no connection to close.")
        self.con.commit()
        self.con.close()
        self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        assert self._con
        return self._con

    def get_media_dir_abs(self, source_name: str) -> Optional[str]:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT media_dir_abs FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert type(result) is tuple and len(result) == 1 and (type(result[0]) in (str, NoneType))
            return result[0]

    def get_media_dir_rel(self, source_name: str) -> str:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT media_dir FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert len(result) == 1 and type(result[0]) is str
            return result[0]

    def get_original_url(self, source_name: str) -> Optional[str]:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT original_url FROM meta WHERE source_name = ? LIMIT 1; """
            result = cur.execute(query, (source_name,)).fetchone()
            assert len(result) == 1 and (type(result[0]) in (str, NoneType))
            return result[0]

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

    def insert_data(self, source_name: str, data: SourceIndex):
        raise_if_invalid_json(data)
        with cursor_buddy(self.con) as cur:
            query = """
            INSERT INTO meta
            (source_name, dictionary_name, year, version, original_url, media_dir, media_dir_abs)
            VALUES(?, ?, ?, ?, ?, ?, ?);
            """
            # Insert meta.
            cur.execute(
                query,
                (
                    source_name,
                    data["meta"]["name"],
                    data["meta"]["year"],
                    data["meta"]["version"],
                    None,
                    data["meta"]["media_dir"],
                    data["meta"].get("media_dir_abs"),  # Possibly unset
                ),
            )
            # Insert headwords and file names
            query = """
                INSERT INTO headwords
                (source_name, headword, file_name)
                VALUES(?, ?, ?);
                """
            cur.executemany(
                query,
                (
                    (source_name, headword, file_name)
                    for headword, file_list in data["headwords"].items()
                    for file_name in file_list
                ),
            )
            # Insert readings and accent info.
            query = """
                INSERT INTO files
                ( source_name, file_name, kana_reading, pitch_pattern, pitch_number )
                VALUES(?, ?, ?, ?, ?);
            """
            cur.executemany(
                query,
                (
                    (
                        source_name,
                        file_name,
                        file_info["kana_reading"],
                        file_info.get("pitch_pattern"),
                        file_info.get("pitch_number"),
                    )
                    for file_name, file_info in data["files"].items()
                ),
            )
            self.con.commit()

    def _prepare_tables(self):
        self.prepare_audio_tables()
        self.prepare_pitch_accents_table()

    def prepare_audio_tables(self) -> None:
        with cursor_buddy(self.con) as cur:
            # Note: `source_name` is the name given to the audio source by the user,
            # and it can be arbitrary (e.g. NHK-2016).
            # `dictionary_name` is the name given to the audio source by its creator.
            # E.g. the NHK audio source provided by Ajatt-Tools has `dictionary_name` set to "NHK日本語発音アクセント新辞典".
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meta(
                    source_name TEXT primary key not null,
                    dictionary_name TEXT not null,
                    year INTEGER not null,
                    version INTEGER not null,
                    original_url TEXT,
                    media_dir TEXT not null,
                    media_dir_abs TEXT
                );
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS headwords(
                    source_name TEXT not null,
                    headword TEXT not null,
                    file_name TEXT not null
                );
            """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS files(
                    source_name TEXT not null,
                    file_name TEXT not null,
                    kana_reading TEXT not null,
                    pitch_pattern TEXT,
                    pitch_number TEXT
                );
            """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS index_names ON meta(source_name);
            """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS index_file_names ON headwords(source_name, headword);
            """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS index_file_info ON files(source_name, file_name);
            """
            )

            self.con.commit()

    def search_files_in_source(self, source_name: str, headword: str) -> Iterable[BoundFile]:
        with cursor_buddy(self.con) as cur:
            query = """
            SELECT file_name FROM headwords
            WHERE source_name = ? AND headword = ?;
            """
            results = cur.execute(query, (source_name, headword)).fetchall()
            assert type(results) is list
            return (
                BoundFile(file_name=result_tup[0], source_name=source_name, headword=headword) for result_tup in results
            )

    def search_files(self, headword: str) -> Iterable[BoundFile]:
        with cursor_buddy(self.con) as cur:
            query = """
            SELECT file_name, source_name FROM headwords
            WHERE headword = ?;
            """
            results = cur.execute(query, (headword,)).fetchall()
            assert type(results) is list
            return (
                BoundFile(file_name=result_tup[0], source_name=result_tup[1], headword=headword)
                for result_tup in results
            )

    def get_file_info(self, source_name: str, file_name: str) -> FileInfo:
        with cursor_buddy(self.con) as cur:
            query = """
            SELECT kana_reading, pitch_pattern, pitch_number FROM files
            WHERE source_name = ? AND file_name = ?
            LIMIT 1;
            """
            result = cur.execute(query, (source_name, file_name)).fetchone()
            assert len(result) == 3 and all((type(val) in (str, NoneType)) for val in result)
            return {
                "kana_reading": result[0],
                "pitch_pattern": result[1],
                "pitch_number": result[2],
            }

    def remove_data(self, source_name: str) -> None:
        """
        Remove all info about audio source from the database.
        """
        with cursor_buddy(self.con) as cur:
            queries = (
                """ DELETE FROM meta      WHERE source_name = ?; """,
                """ DELETE FROM headwords WHERE source_name = ?; """,
                """ DELETE FROM files     WHERE source_name = ?; """,
            )
            for query in queries:
                cur.execute(query, (source_name,))
            self.con.commit()

    def distinct_file_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        with cursor_buddy(self.con) as cur:
            # Filenames in different audio sources may collide,
            # although it's not likely with the currently released audio sources.
            # To resolve collisions when counting distinct filenames,
            # dictionary_name and year are also taken into account.
            query = """
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT f.file_name, m.dictionary_name, m.year FROM files f
                    INNER JOIN meta m ON f.source_name = m.source_name
                    WHERE %s
                );
            """
            result = cur.execute(
                query % build_or_clause("f.source_name", len(source_names)),
                source_names,
            ).fetchone()
            assert len(result) == 1
            return result[0]

    def distinct_headword_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        with cursor_buddy(self.con) as cur:
            query = """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords WHERE %s); """
            # Return the number of unique headwords in the specified sources.
            result = cur.execute(
                query % build_or_clause("source_name", len(source_names)),
                source_names,
            ).fetchone()
            assert len(result) == 1
            return result[0]

    def source_names(self) -> list[str]:
        with cursor_buddy(self.con) as cur:
            query_result = cur.execute(""" SELECT source_name FROM meta; """).fetchall()
            return [result_tuple[0] for result_tuple in query_result]

    def get_pitch_accents_headword_count(self) -> int:
        with cursor_buddy(self.con) as cur:
            query = """ SELECT COUNT(DISTINCT headword) FROM pitch_accents_formatted; """
            result = cur.execute(query).fetchone()
            assert len(result) == 1
            return int(result[0])

    def prepare_pitch_accents_table(self) -> None:
        with cursor_buddy(self.con) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS pitch_accents_formatted(
                    headword TEXT not null,
                    katakana_reading TEXT not null,
                    html_notation TEXT not null,
                    pitch_number TEXT not null,
                    frequency INTEGER not null,
                    source TEXT not null
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS index_pitch_accents_headword
                ON pitch_accents_formatted(headword);
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS index_pitch_accents_reading
                ON pitch_accents_formatted(katakana_reading);
                """
            )
            cur.execute(
                # Filtering by source is used when retrieving results and when reloading the user's override table.
                """
                CREATE INDEX IF NOT EXISTS index_pitch_accents_source
                ON pitch_accents_formatted(source);
                """
            )
            self.con.commit()

    def insert_pitch_accent_data(self, rows: typing.Iterable[AccDictRawTSVEntry], provider_name: str) -> None:
        with cursor_buddy(self.con) as cur:
            query = """
            INSERT INTO pitch_accents_formatted
            (headword, katakana_reading, html_notation, pitch_number, frequency, source)
            VALUES(?, ?, ?, ?, ?, ?);
            """
            cur.executemany(
                query,
                (
                    (
                        row["headword"],
                        row["katakana_reading"],
                        row["html_notation"],
                        row["pitch_number"],
                        int(row["frequency"]),
                        provider_name,
                    )
                    for row in rows
                ),
            )
            self.con.commit()

    PITCH_RETRIEVE_KEYS = ("katakana_reading", "html_notation", "pitch_number")

    def search_pitch_accents(
        self, word: Optional[str], prefer_provider_name: str, select_keys: Sequence[str] = PITCH_RETRIEVE_KEYS
    ) -> list[Sequence[str]]:
        with cursor_buddy(self.con) as cur:
            # The user overrides the default (bundled) rows with their own data.
            # Return relevant rows from the user's data if they can be found.
            # Otherwise, return all results for the target word.
            query = f"""
            SELECT DISTINCT {', '.join(select_keys)} FROM (
                WITH all_results AS (
                    SELECT * FROM pitch_accents_formatted
                    WHERE ( headword = ? OR katakana_reading = ? )
                ),
                preferred_results AS (
                    SELECT * FROM all_results
                    WHERE source = ?
                )
                SELECT * FROM preferred_results
                UNION ALL
                SELECT * FROM all_results WHERE NOT EXISTS (SELECT 1 FROM preferred_results)
            )
            ORDER BY frequency DESC, pitch_number ASC, katakana_reading ASC ;
            """
            result = cur.execute(query, (word, word, prefer_provider_name)).fetchall()
            # example row
            # [
            # ('僕', 'ボク', '<low_rise>ボ</low_rise><high>ク</high>', '0', 42378, 'bundled'),
            # ('僕', 'ボク', '<high_drop>ボ</high_drop><low>ク</low>', '1', 42378, 'bundled'),
            # ...
            # ]
            return result

    def clear_pitch_accents_table(self) -> None:
        """
        Remove all pitch accent entries.
        """
        with cursor_buddy(self.con) as cur:
            query = """ DELETE FROM pitch_accents_formatted; """
            cur.execute(query)
            self.con.commit()

    def clear_pitch_accents(self, provider_name: str) -> None:
        with cursor_buddy(self.con) as cur:
            query = """
            DELETE FROM pitch_accents_formatted
            WHERE source = ? ;
            """
            cur.execute(query, (provider_name,))
            self.con.commit()

    def delete_pitch_accents_table(self) -> None:
        with cursor_buddy(self.con) as cur:
            query = """ DROP TABLE pitch_accents_formatted; """
            cur.execute(query)
            self.con.commit()

    def clear_all_audio_data(self) -> None:
        """
        Remove all info about audio sources from the database.
        """
        with cursor_buddy(self.con) as cur:
            queries = """ DELETE FROM meta ; DELETE FROM headwords ; DELETE FROM files ; """
            cur.executescript(queries)
            self.con.commit()

    def __enter__(self):
        """
        Create a temporary connection.
        Use when working in a different thread since the same connection can't be reused in another thread.
        """
        assert self._con is None
        self.start_session()
        assert self._con is not None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Clean up a temporary connection.
        Use when working in a different thread since the same connection can't be reused in another thread.
        """
        self.end_session()
