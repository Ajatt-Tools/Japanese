# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.audio_manager.basic_types import FileUrlData
from japanese.audio_manager.download_results import (
    BLOOP_FILE,
    ReservedFile,
    calc_tooltip_offset,
    only_missing,
)


def make_file_url_data(desired_filename: str = "test.mp3") -> FileUrlData:
    return FileUrlData(
        url="https://example.com/test.mp3",
        desired_filename=desired_filename,
        word="テスト",
        source_name="TestSource",
    )


def make_reserved(
    desired_filename: str = "test.mp3",
    actual_filename: str = "test.mp3",
    already_exists: bool = False,
) -> ReservedFile:
    return ReservedFile(
        source=make_file_url_data(desired_filename),
        actual_filename=actual_filename,
        already_exists=already_exists,
    )


class TestOnlyMissing:
    @pytest.mark.parametrize(
        "reserved, expected_count",
        [
            ([make_reserved(already_exists=False)], 1),
            ([make_reserved(already_exists=True)], 0),
            (
                [
                    make_reserved("a.mp3", already_exists=False),
                    make_reserved("b.mp3", already_exists=True),
                    make_reserved("c.mp3", already_exists=False),
                ],
                2,
            ),
            ([], 0),
        ],
    )
    def test_filter(self, reserved: list[ReservedFile], expected_count: int) -> None:
        assert len(list(only_missing(reserved))) == expected_count


class TestCalcTooltipOffset:
    @pytest.mark.parametrize(
        "n_lines, expected",
        [
            (0, 80),
            (1, 98),
            (5, 170),
            (10, 260),
        ],
    )
    def test_offset(self, n_lines: int, expected: int) -> None:
        assert calc_tooltip_offset(n_lines) == expected


class TestBloopFile:
    def test_bloop_exists(self) -> None:
        assert BLOOP_FILE.is_file()

    def test_bloop_nonempty(self) -> None:
        assert BLOOP_FILE.stat().st_size > 0
