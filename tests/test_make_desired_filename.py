# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import Optional

import pytest

from japanese.audio_manager.source_manager import make_desired_filename
from japanese.database.audio_buddy import BoundFile
from japanese.helpers.audio_json_schema import FileInfo
from japanese.pitch_accents.consts import NO_ACCENT


def make_bound_file(
    headword: str = "単語",
    file_name: str = "word.ogg",
    source_name: str = "NHK",
) -> BoundFile:
    return BoundFile(headword=headword, file_name=file_name, source_name=source_name)


def make_file_info(
    kana_reading: str = "",
    pitch_pattern: str | None = None,
    pitch_number: str | None = None,
) -> FileInfo:
    return FileInfo(kana_reading=kana_reading, pitch_pattern=pitch_pattern, pitch_number=pitch_number)


class TestMakeDesiredFilename:
    @pytest.mark.parametrize(
        "file, file_info, expected",
        [
            # Full: headword + reading + pitch_number + source
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="たんご", pitch_pattern=None, pitch_number="1"),
                "単語_タンゴ_1_nhk.ogg",
            ),
            # Pitch pattern preferred over kana reading
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="たんご", pitch_pattern="タンゴ", pitch_number="0"),
                "単語_タンゴ_0_nhk.ogg",
            ),
            # No reading at all -> reading component skipped
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="", pitch_pattern=None, pitch_number="1"),
                "単語_1_nhk.ogg",
            ),
            # NO_ACCENT pitch number -> skipped
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="たんご", pitch_pattern=None, pitch_number=NO_ACCENT),
                "単語_タンゴ_nhk.ogg",
            ),
            # Empty pitch number -> skipped
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="たんご", pitch_pattern=None, pitch_number=""),
                "単語_タンゴ_nhk.ogg",
            ),
            # Only headword + source
            (
                make_bound_file("単語", "word.ogg", "NHK"),
                make_file_info(kana_reading="", pitch_pattern=None, pitch_number=None),
                "単語_nhk.ogg",
            ),
            # Multiple pitch numbers (dash-separated)
            (
                make_bound_file("作用", "word.mp3", "Source"),
                make_file_info(kana_reading="さよう", pitch_pattern=None, pitch_number="1-3-0"),
                "作用_サヨウ_1-3-0_source.mp3",
            ),
        ],
    )
    def test_make_desired_filename(self, file: BoundFile, file_info: FileInfo, expected: str) -> None:
        assert make_desired_filename(file, file_info) == expected
