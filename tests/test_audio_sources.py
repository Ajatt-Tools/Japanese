# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.audio_manager.audio_source import AudioSource
from japanese.database.sqlite3_buddy import Sqlite3Buddy
from playground.utils import NoAnkiConfigView
from tests.conftest import tmp_db_connection


def some_media_dir() -> str:
    return "https://raw.githubusercontent.com/Ajatt-Tools/nhk_2016_pronunciations_index/main/media"


def test_source_join_remote(
    no_anki_config: NoAnkiConfigView, monkeypatch: pytest.MonkeyPatch, tmp_db_connection: Sqlite3Buddy
) -> None:
    monkeypatch.setattr(AudioSource, "is_cached", lambda _self: True)
    monkeypatch.setattr(AudioSource, "is_local", False)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_abs", lambda _self, _name: some_media_dir())
    source = AudioSource(enabled=True, name="Test 1", url="https://example.com", db=tmp_db_connection)
    assert source.media_dir == some_media_dir()
    assert source.join_media_path(source.media_dir, "filename.ogg") == f"{some_media_dir()}/filename.ogg"


def test_source_join_local(
    no_anki_config: NoAnkiConfigView, monkeypatch: pytest.MonkeyPatch, tmp_db_connection: Sqlite3Buddy
) -> None:
    monkeypatch.setattr(AudioSource, "is_cached", lambda _self: True)
    monkeypatch.setattr(AudioSource, "is_local", True)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_abs", lambda _self, _name: None)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_rel", lambda _self, _name: "media")
    source = AudioSource(enabled=True, name="Test 2", url="/path/to/index.json", db=tmp_db_connection)
    assert source.media_dir == "/path/to/media"
    assert source.join_media_path(source.media_dir, "filename.ogg") == "/path/to/media/filename.ogg"
