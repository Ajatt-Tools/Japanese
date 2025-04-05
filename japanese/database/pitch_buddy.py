# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import typing
from typing import Optional, Sequence

from ..pitch_accents.common import AccDictRawTSVEntry
from .basic_types import Sqlite3Buddy, cursor_buddy


class PitchSqlite3Buddy:
    def prepare_pitch_accents_table(self: Sqlite3Buddy) -> None:
        pitch_tables_schema = """
        CREATE TABLE IF NOT EXISTS pitch_accents_formatted(
            headword TEXT not null,
            katakana_reading TEXT not null,
            html_notation TEXT not null,
            pitch_number TEXT not null,
            frequency INTEGER not null,
            source TEXT not null
        );

        CREATE INDEX IF NOT EXISTS index_pitch_accents_headword
        ON pitch_accents_formatted(headword);

        CREATE INDEX IF NOT EXISTS index_pitch_accents_reading
        ON pitch_accents_formatted(katakana_reading);

        -- Filtering by source is used when retrieving results and when reloading the user's override table.
        CREATE INDEX IF NOT EXISTS index_pitch_accents_source
        ON pitch_accents_formatted(source);
        """
        with cursor_buddy(self.con) as cur:
            cur.executescript(pitch_tables_schema)
            self.con.commit()

    def get_pitch_accents_headword_count(self: Sqlite3Buddy) -> int:
        query = """
        SELECT COUNT(DISTINCT headword) FROM pitch_accents_formatted;
        """
        with cursor_buddy(self.con) as cur:
            result = cur.execute(query).fetchone()
            assert len(result) == 1
            return int(result[0])

    def insert_pitch_accent_data(
        self: Sqlite3Buddy, rows: typing.Iterable[AccDictRawTSVEntry], provider_name: str
    ) -> None:
        query = """
        INSERT INTO pitch_accents_formatted
        (headword, katakana_reading, html_notation, pitch_number, frequency, source)
        VALUES(?, ?, ?, ?, ?, ?);
        """
        with cursor_buddy(self.con) as cur:
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
        self: Sqlite3Buddy,
        word: Optional[str],
        prefer_provider_name: str,
        select_keys: Sequence[str] = PITCH_RETRIEVE_KEYS,
    ) -> list[Sequence[str]]:
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
        with cursor_buddy(self.con) as cur:
            result = cur.execute(query, (word, word, prefer_provider_name)).fetchall()
            # example row
            # [
            # ('僕', 'ボク', '<low_rise>ボ</low_rise><high>ク</high>', '0', 42378, 'bundled'),
            # ('僕', 'ボク', '<high_drop>ボ</high_drop><low>ク</low>', '1', 42378, 'bundled'),
            # ...
            # ]
            return result

    def clear_pitch_accents_table(self: Sqlite3Buddy) -> None:
        """
        Remove all pitch accent entries.
        """
        query = """
        DELETE FROM pitch_accents_formatted;
        """
        with cursor_buddy(self.con) as cur:
            cur.execute(query)
            self.con.commit()

    def clear_pitch_accents(self: Sqlite3Buddy, provider_name: str) -> None:
        query = """
        DELETE FROM pitch_accents_formatted
        WHERE source = ? ;
        """
        with cursor_buddy(self.con) as cur:
            cur.execute(query, (provider_name,))
            self.con.commit()

    def delete_pitch_accents_table(self: Sqlite3Buddy) -> None:
        query = """
        DROP TABLE pitch_accents_formatted;
        """
        with cursor_buddy(self.con) as cur:
            cur.execute(query)
            self.con.commit()
