# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from types import NoneType
from typing import Optional

try:
    from .audio_json_schema import SourceIndex, FileInfo
    from .file_ops import user_files_dir
except ImportError:
    from audio_json_schema import SourceIndex, FileInfo
    from file_ops import user_files_dir

DB_PATH = os.path.join(user_files_dir(), "audio_sources.sqlite3")


class Sqlite3Buddy:
    """ Db holds three tables: ('meta', 'headwords', 'files') """

    def __init__(self):
        self._con: Optional[sqlite3.Connection] = None

    @property
    def can_execute(self):
        return self._con is not None

    @contextmanager
    def new_session(self):
        self.start_session()
        assert self.can_execute
        yield
        self.end_session()

    def start_session(self):
        if self.can_execute:
            self.end_session()
        self._con: sqlite3.Connection = sqlite3.connect(DB_PATH)
        self._prepare_tables()

    def end_session(self):
        if self.can_execute:
            self._con.commit()
            self._con.close()
            self._con = None

    def get_media_dir_abs(self, source_name: str) -> Optional[str]:
        cur = self._con.cursor()
        query = """ SELECT media_dir_abs FROM meta WHERE source_name = ? LIMIT 1; """
        result = cur.execute(query, (source_name,)).fetchone()
        assert type(result) == tuple and len(result) == 1 and (type(result[0]) in (str, NoneType))
        return result[0]

    def get_media_dir_rel(self, source_name: str) -> str:
        cur = self._con.cursor()
        query = """ SELECT media_dir FROM meta WHERE source_name = ? LIMIT 1; """
        return ''.join(cur.execute(query, (source_name,)).fetchone())

    def get_original_url(self, source_name: str) -> Optional[str]:
        cur = self._con.cursor()
        query = """ SELECT original_url FROM meta WHERE source_name = ? LIMIT 1; """
        result = cur.execute(query, (source_name,)).fetchone()
        assert len(result) == 1 and (type(result[0]) in (str, NoneType))
        return result[0]

    def set_original_url(self, source_name: str, new_url: str) -> None:
        cur = self._con.cursor()
        query = """ UPDATE meta SET original_url = ? WHERE source_name = ?; """
        cur.execute(query, (new_url, source_name,))
        self._con.commit()

    def is_source_cached(self, source_name: str) -> bool:
        """ True if audio source with this name has been cached already. """
        cur = self._con.cursor()
        queries = (
            """ SELECT 1 FROM meta      WHERE source_name = ? LIMIT 1; """,
            """ SELECT 1 FROM headwords WHERE source_name = ? LIMIT 1; """,
            """ SELECT 1 FROM files     WHERE source_name = ? LIMIT 1; """,
        )
        return all(
            cur.execute(query, (source_name,)).fetchone() is not None
            for query in queries
        )

    def insert_data(self, source_name: str, data: SourceIndex):
        cur = self._con.cursor()
        query = """
        INSERT INTO meta
        (source_name, year, version, original_url, media_dir, media_dir_abs)
        VALUES(?, ?, ?, ?, ?, ?);
        """
        # Insert meta.
        cur.execute(
            query,
            (
                source_name,
                data['meta']['year'],
                data['meta']['version'],
                None,
                data['meta']['media_dir'],
                data['meta'].get('media_dir_abs'),  # Possibly unset
            )
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
                for headword, file_list in data['headwords'].items()
                for file_name in file_list
            )
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
                    file_info['kana_reading'],
                    file_info.get('pitch_pattern'),
                    file_info.get('pitch_number'),
                )
                for file_name, file_info in data['files'].items()
            )
        )
        self._con.commit()

    def _prepare_tables(self):
        cur = self._con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta(
                source_name TEXT primary key not null,
                year INTEGER not null,
                version INTEGER not null,
                original_url TEXT,
                media_dir TEXT not null,
                media_dir_abs TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS headwords(
                source_name TEXT not null,
                headword TEXT not null,
                file_name TEXT not null
            );
            """)
        cur.execute("""
              CREATE TABLE IF NOT EXISTS files(
                  source_name TEXT not null,
                  file_name TEXT not null,
                  kana_reading TEXT not null,
                  pitch_pattern TEXT,
                  pitch_number TEXT
              );
              """)
        self._con.commit()

    def search_files(self, source_name: str, headword: str) -> Iterable[str]:
        cur = self._con.cursor()
        query = """
        SELECT file_name FROM headwords
        WHERE source_name = ? AND headword = ?;
        """
        results = cur.execute(query, (source_name, headword)).fetchall()
        assert type(results) == list
        return (result_tup[0] for result_tup in results)

    def get_file_info(self, source_name: str, file_name: str) -> FileInfo:
        cur = self._con.cursor()
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

    def remove_data(self, source_name: str):
        cur = self._con.cursor()
        queries = (
            """ DELETE FROM meta      WHERE source_name = ?; """,
            """ DELETE FROM headwords WHERE source_name = ?; """,
            """ DELETE FROM files     WHERE source_name = ?; """,
        )
        for query in queries:
            cur.execute(query, (source_name,))
        self._con.commit()

    def distinct_file_count(self, source_name: Optional[str] = None) -> int:
        cur = self._con.cursor()
        if source_name:
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT file_name FROM files WHERE source_name = ?); """,
                (source_name, )
            ).fetchone()[0]
        else:
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT file_name FROM files); """
            ).fetchone()[0]

    def distinct_headword_count(self, source_name: Optional[str] = None) -> int:
        cur = self._con.cursor()
        if source_name:
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords WHERE source_name = ?); """,
                (source_name, )
            ).fetchone()[0]
        else:
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords); """
            ).fetchone()[0]
