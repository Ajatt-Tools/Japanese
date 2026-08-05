# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import os

from ..database.sqlite3_buddy import Sqlite3Buddy
from ..helpers.file_ops import file_exists
from .basic_types import AudioSourceConfig


class AudioSourceError(RuntimeError):
    """Raised when an audio source is accessed before it is ready."""

    pass


@dataclasses.dataclass
class AudioSource(AudioSourceConfig):
    """Audio source config with database-backed metadata lookups."""

    # current schema has three fields: "meta", "headwords", "files"
    db: Sqlite3Buddy | None

    def with_db(self, db: Sqlite3Buddy | None) -> "AudioSource":
        """Return a copy of this audio source bound to a different database."""
        return dataclasses.replace(self, db=db)

    @classmethod
    def from_cfg(cls, source: AudioSourceConfig, db: Sqlite3Buddy) -> "AudioSource":
        """Create an AudioSource from config and bind it to a database."""
        # noinspection PyTypeChecker
        return cls(**dataclasses.asdict(source), db=db)

    def is_cached(self) -> bool:
        """Return True if this source has been initialized in the database."""
        if not self.db:
            raise AudioSourceError("db is none")
        return self.db.is_source_cached(self.name)

    def raise_if_not_ready(self) -> None:
        """Raise if this source has not been initialized in the database."""
        if not self.is_cached():
            raise AudioSourceError("Attempt to access property of an uninitialized source.")

    @property
    def media_dir(self) -> str:
        """Return the media directory for this source.

        media_dir_abs is returned verbatim when set: release tooling injects it
        as a URL prefix into online indexes, and custom or unreleased sources
        may set it to a local path. Offline indexes never contain it and fall
        back to the media dir beside the source file.
        """
        # Release indexes may specify media_dir_abs as a remote media URL.
        # Custom or unreleased sources may specify it as a local path.
        # Otherwise, fall back to the media dir relative to the source URL.
        self.raise_if_not_ready()
        assert self.db, "db must be set."
        if media_dir_abs := self.db.get_media_dir_abs(self.name):
            return media_dir_abs
        # e.g. if self.url = "/path/to/taas/index.json" and media_dir = "media",
        # then join("/path/to/taas", "media") = "/path/to/taas/media"
        return self._media_dir_rel_to_source()

    def _media_dir_rel_to_source(self) -> str:
        """Return media_dir resolved relative to this source URL."""
        assert self.db, "db must be set."
        return self.join_media_path(os.path.dirname(self.url), self.db.get_media_dir_rel(self.name))

    def join_media_path(self, *args: str) -> str:
        """Join multiple paths."""
        if self.is_local:
            # Local paths are platform-dependent.
            return os.path.join(*args)
        else:
            # URLs are always joined with '/'.
            return "/".join(args)

    @property
    def is_local(self) -> bool:
        """Return True if this source URL points to an existing local file."""
        return file_exists(self.url)

    @property
    def original_url(self) -> str | None:
        """Return the source URL recorded when this source was initialized."""
        self.raise_if_not_ready()
        assert self.db, "db must be set."
        return self.db.get_original_url(self.name)

    def update_original_url(self) -> None:
        """Store the current source URL as the initialized source URL."""
        # Remember where the file was downloaded from.
        self.raise_if_not_ready()
        assert self.db, "db must be set."
        self.db.set_original_url(self.name, self.url)
