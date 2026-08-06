# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import pathlib
import sqlite3
import typing

import pytest

from japanese.audio_manager.audio_source import AudioSource, AudioSourceError
from japanese.audio_manager.basic_types import (
    AudioSourceConfig,
    NameUrl,
    NameUrlSet,
    TotalAudioStats,
)
from japanese.audio_manager.source_manager import AudioSourceManager
from japanese.database.basic_types import InvalidSourceIndex
from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.helpers.audio_json_schema import SourceIndex, SourceMeta
from playground.run_audio_manager import NoAnkiAudioSourceManagerFactory
from playground.utils import NoAnkiConfigView
from tests.conftest import tmp_db_connection, tmp_sqlite3_db_path
from tests.consts import DATA_DIR

REMOTE_SOURCE_URL: typing.Final[str] = "https://example.com/index.json"
REMOTE_MEDIA_DIR: typing.Final[str] = "https://example.com/audio/media"
RELATIVE_MEDIA_DIR: typing.Final[str] = "media"
LOCAL_ABS_MEDIA_DIR: typing.Final[str] = "other-media"


def make_source_index(media_dir_abs: str | None = None) -> SourceIndex:
    """Return a minimal valid audio source index for media-dir tests."""
    data: SourceIndex = {
        "meta": {
            "name": "Test Source",
            "year": 2026,
            "version": 2,
            "media_dir": "media",
        },
        "headwords": {"テスト": ["test.ogg"]},
        "files": {"test.ogg": {"kana_reading": "テスト", "pitch_pattern": None, "pitch_number": None}},
    }
    if media_dir_abs is not None:
        data["meta"]["media_dir_abs"] = media_dir_abs
    return data


def test_source_meta_required_and_optional_keys() -> None:
    """SourceMeta keeps release-injected media_dir_abs optional without weakening required keys."""
    assert SourceMeta.__required_keys__ == frozenset({"name", "year", "version", "media_dir"})
    assert SourceMeta.__optional_keys__ == frozenset({"media_dir_abs"})


def make_cached_source(
    db: Sqlite3Buddy,
    *,
    source_url: str,
    media_dir_abs: str | None = None,
    source_name: str = "TEST",
) -> AudioSource:
    """Insert a minimal source index and return an AudioSource backed by the test database."""
    db.insert_data(source_name, make_source_index(media_dir_abs))
    return AudioSource(name=source_name, url=source_url, enabled=True, db=db)


def make_source_url(tmp_path: pathlib.Path, source_is_local: bool) -> str:
    """Return a local or remote source URL for a media-dir test case."""
    if source_is_local:
        return str(tmp_path / "index.json")
    return REMOTE_SOURCE_URL


def make_media_dir_abs(tmp_path: pathlib.Path, media_dir_abs: str | None) -> str | None:
    """Resolve a parametrized media_dir_abs value for the test filesystem."""
    if media_dir_abs == LOCAL_ABS_MEDIA_DIR:
        return str(tmp_path / LOCAL_ABS_MEDIA_DIR)
    return media_dir_abs


def expected_media_dir(tmp_path: pathlib.Path, source_is_local: bool, media_dir_abs: str | None) -> str:
    """Return the expected resolved media directory for the parametrized source."""
    if resolved_abs := make_media_dir_abs(tmp_path, media_dir_abs):
        return resolved_abs
    if source_is_local:
        return str(tmp_path / RELATIVE_MEDIA_DIR)
    return "/".join((REMOTE_SOURCE_URL.rsplit("/", maxsplit=1)[0], RELATIVE_MEDIA_DIR))


@pytest.fixture()
def init_factory(
    no_anki_config: NoAnkiConfigView, tmp_sqlite3_db_path: pathlib.Path
) -> NoAnkiAudioSourceManagerFactory:
    factory = NoAnkiAudioSourceManagerFactory(config=no_anki_config, db_path=tmp_sqlite3_db_path)
    factory.init_sources()
    return factory


def test_audio_stats(init_factory: NoAnkiAudioSourceManagerFactory, tmp_db_connection: Sqlite3Buddy) -> None:
    session: AudioSourceManager
    stats: TotalAudioStats

    session = init_factory.request_new_session(tmp_db_connection)
    stats = session.total_stats()
    assert stats.unique_files == 19438
    assert stats.unique_headwords == 21569
    assert len(stats.sources) == 1
    assert stats.sources[0].num_files == 19438
    assert stats.sources[0].num_headwords == 21569
    assert len(list(session.search_word("ひらがな"))) == 3


def test_get_sources(
    init_factory: NoAnkiAudioSourceManagerFactory, no_anki_config: NoAnkiConfigView, tmp_db_connection: Sqlite3Buddy
) -> None:
    sources = tmp_db_connection.get_cached_sources()
    assert sources == [NameUrl(s.name, s.url) for s in no_anki_config.iter_audio_sources()]


class TestAudioSourceMediaDir:
    """AudioSource.media_dir returns media_dir_abs verbatim or falls back to the relative media dir."""

    @pytest.mark.parametrize(
        "source_name, source_is_local, media_dir_abs",
        [
            ("TEST_LOCAL_REL", True, None),
            ("TEST_LOCAL_ABS", True, LOCAL_ABS_MEDIA_DIR),
            ("TEST_REMOTE_ABS", False, REMOTE_MEDIA_DIR),
            ("TEST_REMOTE_REL", False, None),
        ],
    )
    def test_resolves_media_dir(
        self,
        tmp_path: pathlib.Path,
        tmp_db_connection: Sqlite3Buddy,
        source_name: str,
        source_is_local: bool,
        media_dir_abs: str | None,
    ) -> None:
        """media_dir_abs wins when present; otherwise media_dir is resolved relative to the source URL."""
        source_url = make_source_url(tmp_path, source_is_local)
        if source_is_local:
            pathlib.Path(source_url).write_text("{}", encoding="utf-8")
        source = make_cached_source(
            tmp_db_connection,
            source_url=source_url,
            media_dir_abs=make_media_dir_abs(tmp_path, media_dir_abs),
            source_name=source_name,
        )
        assert source.media_dir == expected_media_dir(tmp_path, source_is_local, media_dir_abs)


class TestAudioSourceErrors:
    """AudioSource raises AudioSourceError when accessed before it is ready."""

    def test_media_dir_raises_when_not_cached(self, tmp_db_connection: Sqlite3Buddy) -> None:
        """Accessing media_dir on an uninitialized source raises AudioSourceError."""
        source = AudioSource(name="MISSING", url=REMOTE_SOURCE_URL, enabled=True, db=tmp_db_connection)
        with pytest.raises(AudioSourceError):
            source.media_dir

    def test_media_dir_raises_when_db_is_none(self) -> None:
        """Accessing media_dir without a database raises AudioSourceError."""
        source = AudioSource(name="TEST", url=REMOTE_SOURCE_URL, enabled=True, db=None)
        with pytest.raises(AudioSourceError):
            source.media_dir


class TestAudioSourceDbBinding:
    """AudioSource database binding helpers."""

    def test_with_db_returns_distinct_copy(self, tmp_db_connection: Sqlite3Buddy) -> None:
        """with_db returns a new AudioSource bound to the given db, leaving the original unchanged."""
        source = make_cached_source(tmp_db_connection, source_url=REMOTE_SOURCE_URL)
        rebound = source.with_db(None)

        assert rebound is not source
        assert rebound.db is None
        assert rebound.name == source.name
        assert rebound.url == source.url
        assert source.db is tmp_db_connection

    def test_from_cfg_constructs_and_binds(self, tmp_db_connection: Sqlite3Buddy) -> None:
        """from_cfg builds an AudioSource from a config and binds it to the database."""
        cfg = AudioSourceConfig(name="TEST", url=REMOTE_SOURCE_URL, enabled=True)
        source = AudioSource.from_cfg(cfg, tmp_db_connection)

        assert source.name == "TEST"
        assert source.url == REMOTE_SOURCE_URL
        assert source.enabled is True
        assert source.db is tmp_db_connection

    def test_original_url_round_trip(self, tmp_db_connection: Sqlite3Buddy) -> None:
        """update_original_url stores the current url, which original_url reads back."""
        source = make_cached_source(tmp_db_connection, source_url=REMOTE_SOURCE_URL)
        source.update_original_url()

        assert source.original_url == REMOTE_SOURCE_URL


def test_delete_cache(init_factory: NoAnkiAudioSourceManagerFactory, tmp_db_connection: Sqlite3Buddy) -> None:
    session = init_factory.request_new_session(tmp_db_connection)
    stats = session.total_stats()
    assert len(stats.sources) == 1
    test_source = tmp_db_connection.get_source_by_name("TAAS-TEST-BAD")
    assert test_source is None
    test_source = tmp_db_connection.get_source_by_name("TAAS-TEST")
    assert test_source.name == "TAAS-TEST"
    removed = session.remove_sources(NameUrlSet([test_source, NameUrl("TAAS-TEST-BAD", "")]))
    assert removed == [test_source]
    stats = session.total_stats()
    assert len(stats.sources) == 0
    assert stats.unique_files == 0
    assert stats.unique_headwords == 0


def test_insert_bad_source(init_factory: NoAnkiAudioSourceManagerFactory) -> None:
    """
    Vandalize the source on purpose and test if the expected errors are raised.

    Each insert uses a fresh connection: a failed insert_data() leaves its partial
    work uncommitted, and only a new connection (rolled back on __exit__) guarantees
    the next insert starts from a clean state.
    """
    taas_data: SourceIndex = json.loads(DATA_DIR.joinpath("taas_index.json").read_bytes())
    with pytest.raises(sqlite3.IntegrityError):
        # None can't be used according to the schema.
        taas_data["files"]["修理_しゅうり_core6k.1367.ogg"]["kana_reading"] = None  # type: ignore
        with Sqlite3Buddy(init_factory.db_path) as db:
            db.insert_data("fake-source", taas_data)

    with pytest.raises(InvalidSourceIndex):
        # will raise KeyError and caught inside the transaction.
        del taas_data["files"]["修理_しゅうり_core6k.1367.ogg"]["kana_reading"]  # type: ignore
        with Sqlite3Buddy(init_factory.db_path) as db:
            db.insert_data("fake-source", taas_data)

    with pytest.raises(InvalidSourceIndex):
        # audio source file is missing a required key: 'files'
        del taas_data["files"]  # type: ignore
        with Sqlite3Buddy(init_factory.db_path) as db:
            db.insert_data("fake-source", taas_data)
