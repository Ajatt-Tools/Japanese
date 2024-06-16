# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.audio_manager.basic_types import FileUrlData
from japanese.helpers.unique_files import ensure_unique_files


@pytest.fixture(scope="session")
def examples():
    return [
        FileUrlData("/mnt/data/file1.png", "file1.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file1.png", "file2.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file1.png", "file1.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file2.png", "file2.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file2.png", "file1.png", "単語", "NHK"),
    ]


@pytest.fixture(scope="session")
def expected():
    return [
        FileUrlData(
            url="/mnt/data/file1.png",
            desired_filename="file1.png",
            word="単語",
            source_name="NHK",
            reading="",
            pitch_number="?",
        ),
        FileUrlData(
            url="/mnt/data/file2.png",
            desired_filename="file1(1).png",
            word="単語",
            source_name="NHK",
            reading="",
            pitch_number="?",
        ),
    ]


def test_unique_files(examples, expected):
    assert list(ensure_unique_files(examples)) == expected
