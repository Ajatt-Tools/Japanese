# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import json
import pathlib
import sqlite3
import typing

import pytest

from japanese.audio_manager.audio_source import AudioSource
from japanese.audio_manager.basic_types import NameUrl, NameUrlSet, TotalAudioStats
from japanese.audio_manager.source_manager import AudioSourceManager
from japanese.database.basic_types import InvalidSourceIndex
from japanese.database.sqlite3_buddy import Sqlite3Buddy
from japanese.helpers.audio_json_schema import SourceIndex
from playground.run_audio_manager import NoAnkiAudioSourceManagerFactory
from playground.utils import NoAnkiConfigView
from tests.conftest import tmp_sqlite3_db_path
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


def make_cached_source(
    db: Sqlite3Buddy,
    source_url: str,
    media_dir_abs: str | None = None,
    source_name: str = "TEST",
) -> AudioSource:
    """Insert a minimal source index and return an AudioSource backed by the test database."""
    db.insert_data(source_name, make_source_index(media_dir_abs))
    return AudioSource(name=source_name, url=source_url, enabled=True, db=db)


class MediaDirKind(typing.NamedTuple):
    """Scenario input that determines which media_dir_abs value to insert.

    'value' is stored verbatim in the source index meta, or omitted when None.
    'create_dir_name' names a directory to create under tmp_path and use as the
    media_dir_abs value instead, so the scenario can exercise an existing path.
    """

    value: str | None
    create_dir_name: str | None = None


class MediaDirScenario(typing.NamedTuple):
    """Scenario for resolving an audio source media directory."""

    source_name: str
    source_is_local: bool
    media_dir_abs: MediaDirKind
    create_relative_media_dir: bool
    expected_dir_name: str | None


MEDIA_DIR_SCENARIOS: dict[str, MediaDirScenario] = {
    "local_prefers_sibling_media_over_remote_abs": MediaDirScenario(
        source_name="TEST_LOCAL_SIBLING",
        source_is_local=True,
        media_dir_abs=MediaDirKind(REMOTE_MEDIA_DIR),
        create_relative_media_dir=True,
        expected_dir_name=RELATIVE_MEDIA_DIR,
    ),
    "local_existing_abs_takes_precedence": MediaDirScenario(
        source_name="TEST_LOCAL_ABS",
        source_is_local=True,
        media_dir_abs=MediaDirKind(value=None, create_dir_name=LOCAL_ABS_MEDIA_DIR),
        create_relative_media_dir=True,
        expected_dir_name=LOCAL_ABS_MEDIA_DIR,
    ),
    "local_missing_sibling_falls_back_to_remote_abs": MediaDirScenario(
        source_name="TEST_REMOTE_FALLBACK",
        source_is_local=True,
        media_dir_abs=MediaDirKind(REMOTE_MEDIA_DIR),
        create_relative_media_dir=False,
        expected_dir_name=None,
    ),
    "remote_uses_remote_abs": MediaDirScenario(
        source_name="TEST_REMOTE_ABS",
        source_is_local=False,
        media_dir_abs=MediaDirKind(REMOTE_MEDIA_DIR),
        create_relative_media_dir=False,
        expected_dir_name=None,
    ),
    "local_without_abs_uses_sibling_media": MediaDirScenario(
        source_name="TEST_LOCAL_REL",
        source_is_local=True,
        media_dir_abs=MediaDirKind(None),
        create_relative_media_dir=True,
        expected_dir_name=RELATIVE_MEDIA_DIR,
    ),
}


def make_source_url(tmp_path: pathlib.Path, scenario: MediaDirScenario) -> str:
    """Return a local or remote source URL for a media-dir scenario."""
    if scenario.source_is_local:
        return str(tmp_path / "index.json")
    return REMOTE_SOURCE_URL


def make_media_dir_abs(tmp_path: pathlib.Path, scenario: MediaDirScenario) -> str | None:
    """Create and return the scenario's media_dir_abs value."""
    if scenario.media_dir_abs.create_dir_name:
        media_dir = tmp_path / scenario.media_dir_abs.create_dir_name
        media_dir.mkdir()
        return str(media_dir)
    return scenario.media_dir_abs.value


def expected_media_dir(tmp_path: pathlib.Path, scenario: MediaDirScenario) -> str:
    """Return the expected resolved media directory for a scenario."""
    if scenario.expected_dir_name:
        return str(tmp_path / scenario.expected_dir_name)
    assert (
        scenario.media_dir_abs.value is not None
    ), "a scenario without expected_dir_name must declare the media_dir_abs it falls back to"
    return scenario.media_dir_abs.value


@pytest.fixture()
def init_factory(
    no_anki_config: NoAnkiConfigView, tmp_sqlite3_db_path: pathlib.Path
) -> NoAnkiAudioSourceManagerFactory:
    factory = NoAnkiAudioSourceManagerFactory(config=no_anki_config, db_path=tmp_sqlite3_db_path)
    factory.init_sources()
    return factory


def test_audio_stats(init_factory: NoAnkiAudioSourceManagerFactory) -> None:
    session: AudioSourceManager
    stats: TotalAudioStats

    with Sqlite3Buddy(init_factory.db_path) as db:
        session = init_factory.request_new_session(db)
        stats = session.total_stats()
        assert stats.unique_files == 19438
        assert stats.unique_headwords == 21569
        assert len(stats.sources) == 1
        assert stats.sources[0].num_files == 19438
        assert stats.sources[0].num_headwords == 21569
        assert len(list(session.search_word("ひらがな"))) == 3


def test_get_sources(init_factory: NoAnkiAudioSourceManagerFactory, no_anki_config: NoAnkiConfigView) -> None:
    with Sqlite3Buddy(init_factory.db_path) as db:
        sources = db.get_cached_sources()
        assert sources == [NameUrl(s.name, s.url) for s in no_anki_config.iter_audio_sources()]


class TestAudioSourceMediaDir:
    """AudioSource.media_dir prefers a usable local directory over the indexed absolute path."""

    @pytest.mark.parametrize("scenario", MEDIA_DIR_SCENARIOS.values(), ids=list(MEDIA_DIR_SCENARIOS.keys()))
    def test_resolves_media_dir(
        self,
        tmp_path: pathlib.Path,
        tmp_sqlite3_db_path: pathlib.Path,
        scenario: MediaDirScenario,
    ) -> None:
        """AudioSource.media_dir chooses the best usable media directory."""
        if scenario.source_is_local:
            pathlib.Path(make_source_url(tmp_path, scenario)).write_text("{}", encoding="utf-8")
        if scenario.create_relative_media_dir:
            tmp_path.joinpath(RELATIVE_MEDIA_DIR).mkdir()
        with Sqlite3Buddy(tmp_sqlite3_db_path) as db:
            source = make_cached_source(
                db,
                make_source_url(tmp_path, scenario),
                make_media_dir_abs(tmp_path, scenario),
                source_name=scenario.source_name,
            )
            assert source.media_dir == expected_media_dir(tmp_path, scenario)


def test_delete_cache(init_factory: NoAnkiAudioSourceManagerFactory) -> None:
    with Sqlite3Buddy(init_factory.db_path) as db:
        session = init_factory.request_new_session(db)
        stats = session.total_stats()
        assert len(stats.sources) == 1
        test_source = db.get_source_by_name("TAAS-TEST-BAD")
        assert test_source is None
        test_source = db.get_source_by_name("TAAS-TEST")
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
