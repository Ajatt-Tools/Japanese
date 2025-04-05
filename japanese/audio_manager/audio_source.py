# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import os
from typing import Optional, Union

from ..database.sqlite3_buddy import Sqlite3Buddy
from ..helpers.file_ops import file_exists
from .basic_types import AudioSourceConfig


class AudioSourceError(RuntimeError):
    pass


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    db: Optional[Sqlite3Buddy]

    def with_db(self, db: Optional[Sqlite3Buddy]):
        return dataclasses.replace(self, db=db)

    @classmethod
    def from_cfg(cls, source: AudioSourceConfig, db: Sqlite3Buddy) -> "AudioSource":
        # noinspection PyTypeChecker
        return cls(**dataclasses.asdict(source), db=db)

    def is_cached(self) -> bool:
        if not self.db:
            raise AudioSourceError("db is none")
        return self.db.is_source_cached(self.name)

    def raise_if_not_ready(self):
        if not self.is_cached():
            raise AudioSourceError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        # Meta can specify absolute path to the media dir,
        # which will be used if set.
        # Otherwise, fall back to relative path.
        self.raise_if_not_ready()
        assert self.db
        if dir_path_abs := self.db.get_media_dir_abs(self.name):
            return dir_path_abs
        # e.g. if self.url = "/path/to/taas/index.json" and media_dir = "media",
        # then join("/path/to/taas", "media") = "/path/to/taas/media"
        return self.join_media_path(os.path.dirname(self.url), self.db.get_media_dir_rel(self.name))

    def join_media_path(self, *args) -> Union[str, bytes]:
        """Join multiple paths."""
        if self.is_local:
            # Local paths are platform-dependent.
            # noinspection PyArgumentList
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return "/".join(args)

    @property
    def is_local(self) -> bool:
        return file_exists(self.url)

    @property
    def original_url(self):
        self.raise_if_not_ready()
        assert self.db
        return self.db.get_original_url(self.name)

    def update_original_url(self):
        # Remember where the file was downloaded from.
        self.raise_if_not_ready()
        assert self.db
        self.db.set_original_url(self.name, self.url)
