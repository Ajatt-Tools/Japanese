# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import json
from types import SimpleNamespace
from typing import cast
from collections.abc import MutableMapping, Iterable

from japanese.config_view import JapaneseConfig
from japanese.helpers.audio_manager import AudioSourceManagerFactory, AudioSourceManager, TotalAudioStats
from japanese.helpers.file_ops import find_file_in_parents
from japanese.helpers.http_client import AudioSettingsProtocol


@dataclasses.dataclass
class Settings:
    audio_settings: AudioSettingsProtocol
    audio_sources: MutableMapping

    # noinspection PyMethodMayBeStatic
    def iter_audio_sources(self) -> Iterable:
        # NOOP
        yield 1


def init_testing_audio_manager() -> AudioSourceManagerFactory:
    # Used for testing when Anki isn't running.

    with open(find_file_in_parents("meta.json")) as f:
        loaded = json.load(f)["config"]
        cfg = Settings(
            audio_sources=loaded["audio_sources"],
            audio_settings=cast(AudioSettingsProtocol, SimpleNamespace(**loaded["audio_settings"])),
        )

    return AudioSourceManagerFactory(
        config=cast(JapaneseConfig, cfg),
        mgr_class=AudioSourceManager,
    )


def main() -> None:
    factory = init_testing_audio_manager()
    factory.init_sources()
    aud_mgr: AudioSourceManager
    stats: TotalAudioStats

    with factory.request_new_session() as aud_mgr:
        stats = aud_mgr.total_stats()
        print(f"{stats.unique_files=}")
        print(f"{stats.unique_headwords=}")
        for source_stats in stats.sources:
            print(source_stats)
        for file in aud_mgr.search_word("ひらがな"):
            print(file)
        for source in aud_mgr.audio_sources:
            print(f"source {source.name} media dir {source.media_dir}")


if __name__ == "__main__":
    main()
