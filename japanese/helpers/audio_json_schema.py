# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


from typing import NewType, TypedDict

FileList = NewType("FileList", list[str])


class FileInfo(TypedDict):
    kana_reading: str
    pitch_pattern: str | None
    pitch_number: str | None


class SourceMetaRequired(TypedDict):
    name: str
    year: int
    version: int
    media_dir: str


class SourceMeta(SourceMetaRequired, total=False):
    media_dir_abs: str


class SourceIndex(TypedDict):
    meta: SourceMeta
    headwords: dict[str, FileList]
    files: dict[str, FileInfo]
