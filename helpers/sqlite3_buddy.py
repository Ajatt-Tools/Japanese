# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import contextlib
import os
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager

from typing import Optional, NamedTuple

try:
    from .sqlite_schema import CURRENT_DB
    from .audio_json_schema import SourceIndex, FileInfo
    from .file_ops import user_files_dir
except ImportError:
    from sqlite_schema import CURRENT_DB
    from audio_json_schema import SourceIndex, FileInfo
    from file_ops import user_files_dir

NoneType = type(None)  # fix for the official binary bundle

CURRENT_DB.remove_deprecated_files()


class BoundFile(NamedTuple):
    """
    Represents an sqlite query result.
    """
    headword: str
    file_name: str
    source_name: str


class Sqlite3Buddy:
    """ Db holds three tables: ('meta', 'headwords', 'files') """
    _db_path = os.path.join(user_files_dir(), CURRENT_DB.name)

    def __init__(self):
        self._con: Optional[sqlite3.Connection] = None

    @property
    def can_execute(self):
        return self._con is not None

    @classmethod
    @contextmanager
    def new_session(cls):
        """
        Create, use, then clean up a temporary connection.
        Use when working in a different thread since the same connection can't be reused in another thread.
        """
        ins = cls()
        ins.start_session()
        assert ins.can_execute
        yield ins
        ins.end_session()
        del ins

    def start_session(self):
        if self.can_execute:
            self.end_session()
        self._con: sqlite3.Connection = sqlite3.connect(self._db_path)
        self._prepare_tables()

    def end_session(self):
        if self.can_execute:
            self._con.commit()
            self._con.close()
            self._con = None

    @classmethod
    def remove_database_file(cls):
        with contextlib.suppress(FileNotFoundError):
            os.remove(cls._db_path)

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
        (source_name, dictionary_name, year, version, original_url, media_dir, media_dir_abs)
        VALUES(?, ?, ?, ?, ?, ?, ?);
        """
        # Insert meta.
        cur.execute(
            query,
            (
                source_name,
                data['meta']['name'],
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
        # Note: `source_name` is the name given to the audio source by the user,
        # and it can be arbitrary (e.g. NHK-2016).
        # `dictionary_name` is the name given to the audio source by its creator.
        # E.g. the NHK audio source provided by Ajatt-Tools has `dictionary_name` set to "NHK日本語発音アクセント新辞典".
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta(
                source_name TEXT primary key not null,
                dictionary_name TEXT not null,
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
        cur.execute("""
            CREATE INDEX IF NOT EXISTS index_names ON meta(source_name);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS index_file_names ON headwords(source_name, headword);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS index_file_info ON files(source_name, file_name);
        """)

        self._con.commit()
        cur.close()

    def search_files_in_source(self, source_name: str, headword: str) -> Iterable[BoundFile]:
        cur = self._con.cursor()
        query = """
        SELECT file_name FROM headwords
        WHERE source_name = ? AND headword = ?;
        """
        results = cur.execute(query, (source_name, headword)).fetchall()
        assert type(results) == list
        return (
            BoundFile(file_name=result_tup[0], source_name=source_name, headword=headword)
            for result_tup in results
        )

    def search_files(self, headword: str) -> Iterable[BoundFile]:
        cur = self._con.cursor()
        query = """
        SELECT file_name, source_name FROM headwords
        WHERE headword = ?;
        """
        results = cur.execute(query, (headword,)).fetchall()
        assert type(results) == list
        return (
            BoundFile(file_name=result_tup[0], source_name=result_tup[1], headword=headword)
            for result_tup in results
        )

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
            # If the audio source is known (NHK, Shinmeikai, etc.), simply count files.
            # Each file is guaranteed to have a unique name.
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT file_name FROM files WHERE source_name = ?); """,
                (source_name,)
            ).fetchone()[0]
        else:
            # Filenames in different audio sources may collide,
            # although it's not likely with the currently released audio sources.
            # To resolve collisions when counting distinct filenames,
            # dictionary name and year are also taken into account.
            return cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT f.file_name, m.dictionary_name, m.year FROM files f
                    INNER JOIN meta m ON f.source_name = m.source_name
                );
            """).fetchone()[0]

    def distinct_headword_count(self, source_name: Optional[str] = None) -> int:
        cur = self._con.cursor()
        if source_name:
            # If the audio source is known, simply count headwords.
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords WHERE source_name = ?); """,
                (source_name,)
            ).fetchone()[0]
        else:
            # Return the number of unique headwords in all sources.
            return cur.execute(
                """ SELECT COUNT(*) FROM (SELECT DISTINCT headword FROM headwords); """
            ).fetchone()[0]


# Debug
##########################################################################


def main():
    with Sqlite3Buddy.new_session() as s:
        print(f"word count: {s.distinct_headword_count()}")
        print(f"file count: {s.distinct_file_count()}")


if __name__ == '__main__':
    main()
