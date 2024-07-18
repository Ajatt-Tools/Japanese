# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.audio_manager.audio_source import AudioSource
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy
from tests.no_anki_config import NoAnkiConfigView, no_anki_config


def some_media_dir() -> str:
    return "https://raw.githubusercontent.com/Ajatt-Tools/nhk_2016_pronunciations_index/main/media"


def test_source_join_remote(no_anki_config: NoAnkiConfigView, monkeypatch) -> None:
    monkeypatch.setattr(AudioSource, "is_cached", lambda _self: True)
    monkeypatch.setattr(AudioSource, "is_local", False)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_abs", lambda _self, _name: some_media_dir())
    with Sqlite3Buddy() as db:
        source = AudioSource(enabled=True, name="Test 1", url="https://example.com", db=db)
        assert source.media_dir == some_media_dir()
        assert source.join(source.media_dir, "filename.ogg") == f"{some_media_dir()}/filename.ogg"


def test_source_join_local(no_anki_config: NoAnkiConfigView, monkeypatch) -> None:
    monkeypatch.setattr(AudioSource, "is_cached", lambda _self: True)
    monkeypatch.setattr(AudioSource, "is_local", True)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_abs", lambda _self, _name: None)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_rel", lambda _self, _name: "media")
    with Sqlite3Buddy() as db:
        source = AudioSource(enabled=True, name="Test 2", url="/path/to/index.json", db=db)
        assert source.media_dir == "/path/to/media"
        assert source.join(source.media_dir, "filename.ogg") == f"/path/to/media/filename.ogg"
