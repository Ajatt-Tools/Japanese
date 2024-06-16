# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import os
import posixpath
from typing import Optional, Union

from ..helpers.file_ops import file_exists
from ..helpers.sqlite3_buddy import Sqlite3Buddy
from .basic_types import AudioSourceConfig


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    db: Optional[Sqlite3Buddy]

    def with_db(self, db: Optional[Sqlite3Buddy]):
        return dataclasses.replace(self, db=db)

    @classmethod
    def from_cfg(cls, source: AudioSourceConfig, db: Sqlite3Buddy) -> "AudioSource":
        return cls(**dataclasses.asdict(source), db=db)

    def to_cfg(self) -> AudioSourceConfig:
        """
        Used to compare changes in the config file.
        """
        data = dataclasses.asdict(self)
        del data["db"]
        return AudioSourceConfig(**data)

    def is_cached(self) -> bool:
        if not self.db:
            raise RuntimeError("db is none")
        return self.db.is_source_cached(self.name)

    def raise_if_not_ready(self):
        if not self.is_cached():
            raise RuntimeError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        # Meta can specify absolute path to the media dir,
        # which will be used if set.
        # Otherwise, fall back to relative path.
        self.raise_if_not_ready()
        assert self.db
        dir_path_abs = self.db.get_media_dir_abs(self.name)
        if not dir_path_abs:
            dir_path_abs = self.join(os.path.dirname(self.url), self.db.get_media_dir_rel(self.name))
        return dir_path_abs

    def join(self, *args) -> Union[str, bytes]:
        """Join multiple paths."""
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return '/'.join(*args)

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

    def distinct_file_count(self) -> int:
        self.raise_if_not_ready()
        assert self.db
        return self.db.distinct_file_count(source_names=(self.name,))

    def distinct_headword_count(self) -> int:
        self.raise_if_not_ready()
        assert self.db
        return self.db.distinct_headword_count(source_names=(self.name,))
