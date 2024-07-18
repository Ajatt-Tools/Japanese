# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import contextlib
import os
import sqlite3
import typing
from collections.abc import Iterable, Sequence
from typing import NamedTuple, Optional

from ..pitch_accents.common import AccDictRawTSVEntry
from .audio_json_schema import FileInfo, SourceIndex
from .file_ops import user_files_dir
from .sqlite_schema import CURRENT_DB

NoneType = type(None)  # fix for the official binary bundle

CURRENT_DB.remove_deprecated_files()


class BoundFile(NamedTuple):
    """
    Represents an sqlite query result.
    """

    headword: str
    file_name: str
    source_name: str


def build_or_clause(repeated_field_name: str, count: int) -> str:
    return " OR ".join(f"{repeated_field_name} = ?" for _idx in range(count))


class Sqlite3Buddy:
    """
    Tables for audio:  ('meta', 'headwords', 'files')
    Table for pitch accents: 'pitch_accents_formatted'
    """

    _db_path: str = os.path.join(user_files_dir(), CURRENT_DB.name)
    _con: Optional[sqlite3.Connection]

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or self._db_path
        print(self._db_path)
        self._con = None

    def can_execute(self) -> bool:
        return self._con is not None

    def start_session(self) -> None:
        if self.can_execute():
            self.end_session()
        self._con: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._prepare_tables()

    def end_session(self) -> None:
        if self.can_execute():
            self.con.commit()
            self.con.close()
            self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        assert self._con
        return self._con

    @classmethod
    def remove_database_file(cls):
        with contextlib.suppress(FileNotFoundError):
            os.remove(cls._db_path)

    def get_media_dir_abs(self, source_name: str) -> Optional[str]:
        cur = self.con.cursor()
        query = """ SELECT media_dir_abs FROM meta WHERE source_name = ? LIMIT 1; """
        result = cur.execute(query, (source_name,)).fetchone()
        assert type(result) is tuple and len(result) == 1 and (type(result[0]) in (str, NoneType))
        cur.close()
        return result[0]

    def get_media_dir_rel(self, source_name: str) -> str:
        cur = self.con.cursor()
        query = """ SELECT media_dir FROM meta WHERE source_name = ? LIMIT 1; """
        result = cur.execute(query, (source_name,)).fetchone()
        assert len(result) == 1 and type(result[0]) is str
        cur.close()
        return result[0]

    def get_original_url(self, source_name: str) -> Optional[str]:
        cur = self.con.cursor()
        query = """ SELECT original_url FROM meta WHERE source_name = ? LIMIT 1; """
        result = cur.execute(query, (source_name,)).fetchone()
        assert len(result) == 1 and (type(result[0]) in (str, NoneType))
        cur.close()
        return result[0]

    def set_original_url(self, source_name: str, new_url: str) -> None:
        cur = self.con.cursor()
        query = """ UPDATE meta SET original_url = ? WHERE source_name = ?; """
        cur.execute(query, (new_url, source_name))
        self.con.commit()
        cur.close()

    def is_source_cached(self, source_name: str) -> bool:
        """True if audio source with this name has been cached already."""
        cur = self.con.cursor()
        queries = (
            """ SELECT 1 FROM meta      WHERE source_name = ? LIMIT 1; """,
            """ SELECT 1 FROM headwords WHERE source_name = ? LIMIT 1; """,
            """ SELECT 1 FROM files     WHERE source_name = ? LIMIT 1; """,
        )
        results = [cur.execute(query, (source_name,)).fetchone() for query in queries]
        cur.close()
        return all(result is not None for result in results)

    def insert_data(self, source_name: str, data: SourceIndex):
        cur = self.con.cursor()
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
        cur.close()

    def _prepare_tables(self):
        self.prepare_audio_tables()
        self.prepare_pitch_accents_table()

    def prepare_audio_tables(self) -> None:
        cur = self.con.cursor()
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
        cur.close()

    def search_files_in_source(self, source_name: str, headword: str) -> Iterable[BoundFile]:
        cur = self.con.cursor()
        query = """
        SELECT file_name FROM headwords
        WHERE source_name = ? AND headword = ?;
        """
        results = cur.execute(query, (source_name, headword)).fetchall()
        assert type(results) is list
        cur.close()
        return (
            BoundFile(file_name=result_tup[0], source_name=source_name, headword=headword) for result_tup in results
        )

    def search_files(self, headword: str) -> Iterable[BoundFile]:
        cur = self.con.cursor()
        query = """
        SELECT file_name, source_name FROM headwords
        WHERE headword = ?;
        """
        results = cur.execute(query, (headword,)).fetchall()
        assert type(results) is list
        cur.close()
        return (
            BoundFile(file_name=result_tup[0], source_name=result_tup[1], headword=headword) for result_tup in results
        )

    def get_file_info(self, source_name: str, file_name: str) -> FileInfo:
        cur = self.con.cursor()
        query = """
        SELECT kana_reading, pitch_pattern, pitch_number FROM files
        WHERE source_name = ? AND file_name = ?
        LIMIT 1;
        """
        result = cur.execute(query, (source_name, file_name)).fetchone()
        assert len(result) == 3 and all((type(val) in (str, NoneType)) for val in result)
        cur.close()
        return {
            "kana_reading": result[0],
            "pitch_pattern": result[1],
            "pitch_number": result[2],
        }

    def remove_data(self, source_name: str) -> None:
        """
        Remove all info about audio source from the database.
        """
        cur = self.con.cursor()
        queries = (
            """ DELETE FROM meta      WHERE source_name = ?; """,
            """ DELETE FROM headwords WHERE source_name = ?; """,
            """ DELETE FROM files     WHERE source_name = ?; """,
        )
        for query in queries:
            cur.execute(query, (source_name,))
        self.con.commit()
        cur.close()

    def distinct_file_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        cur = self.con.cursor()
        # Filenames in different audio sources may collide,
        # although it's not likely with the currently released audio sources.
        # To resolve collisions when counting distinct filenames,
        # dictionary name and year are also taken into account.
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
        cur.close()
        return result[0]

    def distinct_headword_count(self, source_names: Sequence[str]) -> int:
        if not source_names:
            return 0
        cur = self.con.cursor()
        query = """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords WHERE %s); """
        # Return the number of unique headwords in the specified sources.
        result = cur.execute(
            query % build_or_clause("source_name", len(source_names)),
            source_names,
        ).fetchone()
        assert len(result) == 1
        cur.close()
        return result[0]

    def source_names(self) -> list[str]:
        cur = self.con.cursor()
        query_result = cur.execute(""" SELECT source_name FROM meta; """).fetchall()
        cur.close()
        return [result_tuple[0] for result_tuple in query_result]

    def get_pitch_accents_headword_count(self) -> int:
        cur = self.con.cursor()
        query = """ SELECT COUNT(DISTINCT headword) FROM pitch_accents_formatted; """
        result = cur.execute(query).fetchone()
        assert len(result) == 1
        cur.close()
        return int(result[0])

    def prepare_pitch_accents_table(self) -> None:
        cur = self.con.cursor()
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
            CREATE INDEX IF NOT EXISTS index_names ON pitch_accents_formatted(headword, katakana_reading, source);
        """
        )
        self.con.commit()
        cur.close()

    def insert_pitch_accent_data(self, rows: typing.Iterable[AccDictRawTSVEntry], provider_name: str) -> None:
        cur = self.con.cursor()
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
        cur.close()

    def clear_pitch_accents_table(self) -> None:
        cur = self.con.cursor()
        query = """ DELETE FROM pitch_accents_formatted; """
        cur.execute(query)
        self.con.commit()
        cur.close()

    def delete_pitch_accents_table(self) -> None:
        cur = self.con.cursor()
        query = """ DROP TABLE pitch_accents_formatted; """
        cur.execute(query)
        self.con.commit()
        cur.close()

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
        del self
