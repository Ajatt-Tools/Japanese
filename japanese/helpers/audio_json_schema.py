# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


from typing import NewType, TypedDict

FileList = NewType("FileList", list[str])


class FileInfo(TypedDict):
    kana_reading: str
    pitch_pattern: str
    pitch_number: str


class SourceMeta(TypedDict):
    name: str
    year: int
    version: int
    media_dir: str
    media_dir_abs: str


class SourceIndex(TypedDict):
    meta: SourceMeta
    headwords: dict[str, FileList]
    files: dict[str, FileInfo]
