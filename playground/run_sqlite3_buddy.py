# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from japanese.helpers.sqlite3_buddy import Sqlite3Buddy


def main() -> None:
    s: Sqlite3Buddy
    with Sqlite3Buddy() as s:
        source_names = s.source_names()
        print(f"source names: {source_names}")
        print(f"word count: {s.distinct_headword_count(source_names)}")
        print(f"file count: {s.distinct_file_count(source_names)}")


if __name__ == "__main__":
    main()
