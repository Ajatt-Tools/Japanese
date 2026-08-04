# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import os
from typing import Any, Optional, Union

from ..database.sqlite3_buddy import Sqlite3Buddy
from ..helpers.file_ops import file_exists
from .basic_types import AudioSourceConfig


class AudioSourceError(RuntimeError):
    pass


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    # current schema has three fields: "meta", "headwords", "files"
    db: Sqlite3Buddy | None

    def with_db(self, db: Sqlite3Buddy | None) -> "AudioSource":
        return dataclasses.replace(self, db=db)

    @classmethod
    def from_cfg(cls, source: AudioSourceConfig, db: Sqlite3Buddy) -> "AudioSource":
        # noinspection PyTypeChecker
        return cls(**dataclasses.asdict(source), db=db)

    def is_cached(self) -> bool:
        if not self.db:
            raise AudioSourceError("db is none")
        return self.db.is_source_cached(self.name)

    def raise_if_not_ready(self) -> None:
        if not self.is_cached():
            raise AudioSourceError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        """Return the best available media directory for this source."""
        # Release indexes may specify media_dir_abs as a remote media URL.
        # For local/offline indexes, prefer an existing local media_dir beside index.json.
        # Existing local media_dir_abs is still supported for custom source layouts.
        self.raise_if_not_ready()
        assert self.db

        media_dir_abs = self.db.get_media_dir_abs(self.name)

        if media_dir_abs and os.path.isdir(media_dir_abs):
            return media_dir_abs

        if self.is_local and os.path.isdir(local_media_dir := self._media_dir_rel_to_source()):
            return local_media_dir

        # Official release indexes may contain a remote media_dir_abs injected by release tooling.
        if media_dir_abs:
            return media_dir_abs

        # e.g. if self.url = "/path/to/taas/index.json" and media_dir = "media",
        # then join("/path/to/taas", "media") = "/path/to/taas/media"
        return self._media_dir_rel_to_source()

    def _media_dir_rel_to_source(self) -> str:
        """Return media_dir resolved relative to this source URL."""
        assert self.db
        return self.join_media_path(os.path.dirname(self.url), self.db.get_media_dir_rel(self.name))

    def join_media_path(self, *args) -> str:
        """Join multiple paths."""
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return "/".join(args)

    @property
    def is_local(self) -> bool:
        return file_exists(self.url)

    @property
    def original_url(self) -> str | None:
        self.raise_if_not_ready()
        assert self.db
        return self.db.get_original_url(self.name)

    def update_original_url(self) -> None:
        # Remember where the file was downloaded from.
        self.raise_if_not_ready()
        assert self.db
        self.db.set_original_url(self.name, self.url)
