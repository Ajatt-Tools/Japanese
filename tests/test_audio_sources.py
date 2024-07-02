# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.audio_manager.audio_source import AudioSource
from japanese.helpers.sqlite3_buddy import Sqlite3Buddy, sqlite3_buddy
from tests.no_anki_config import NoAnkiConfigView, no_anki_config


def some_media_dir() -> str:
    return "https://raw.githubusercontent.com/Ajatt-Tools/nhk_2016_pronunciations_index/main/media"


def get_test_source(db: Sqlite3Buddy) -> AudioSource:
    return AudioSource(enabled=True, name="Test", url="https://example.com", db=db)


def test_source_join(no_anki_config: NoAnkiConfigView, monkeypatch) -> None:
    monkeypatch.setattr(AudioSource, "is_cached", lambda _self: True)
    monkeypatch.setattr(AudioSource, "is_local", False)
    monkeypatch.setattr(Sqlite3Buddy, "get_media_dir_abs", lambda _self, _name: some_media_dir())
    with sqlite3_buddy() as db:
        source = get_test_source(db)
        assert source.media_dir == some_media_dir()
        assert source.join(source.media_dir, "filename.ogg") == f"{some_media_dir()}/filename.ogg"
