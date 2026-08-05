# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html


from typing import NewType, TypedDict

FileList = NewType("FileList", list[str])


class FileInfo(TypedDict):
    """Per-file pitch accent metadata in an audio source index."""

    kana_reading: str
    pitch_pattern: str | None
    pitch_number: str | None


class SourceMetaRequired(TypedDict):
    """Required metadata of an audio source index."""

    name: str
    year: int
    version: int
    media_dir: str


class SourceMeta(SourceMetaRequired, total=False):
    """Audio source metadata; media_dir_abs is optional.

    media_dir_abs is usually injected by release tooling as a URL prefix into
    online (release) indexes, but custom or unreleased sources may set it to a
    local path. Offline (local) indexes never contain it.
    typing.NotRequired is avoided because it is unavailable on the Python versions Anki supports.
    """

    media_dir_abs: str


class SourceIndex(TypedDict):
    """Top-level schema of an audio source index.json file."""

    meta: SourceMeta
    headwords: dict[str, FileList]
    files: dict[str, FileInfo]
