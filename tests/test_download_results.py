# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib

import pytest

import japanese.audio_manager.download_results as download_results
from japanese.audio_manager.basic_types import FileUrlData
from japanese.audio_manager.download_results import (
    BLOOP_FILE,
    ReservedFile,
    bloop_data,
    calc_tooltip_offset,
    is_bloop_placeholder,
    only_missing,
    reserve_files,
)


class FakeMediaManager:
    """Minimal media manager for testing reservation behavior."""

    def __init__(self, media_dir: str) -> None:
        self._media_dir = media_dir
        self.write_calls: list[tuple[str, bytes]] = []

    def dir(self) -> str:
        return self._media_dir

    def have(self, filename: str) -> bool:
        return (pathlib.Path(self._media_dir) / filename).exists()

    def write_data(self, desired_fname: str, data: bytes) -> str:
        self.write_calls.append((desired_fname, data))
        pathlib.Path(self._media_dir, desired_fname).write_bytes(data)
        return desired_fname


class FakeCollection:
    def __init__(self, media: FakeMediaManager) -> None:
        self.media = media


class FakeMainWindow:
    def __init__(self, col: FakeCollection) -> None:
        self.col = col


@pytest.fixture()
def fake_media(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> FakeMediaManager:
    media = FakeMediaManager(str(tmp_path))
    monkeypatch.setattr(download_results, "mw", FakeMainWindow(FakeCollection(media)))
    return media


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


class TestReserveFiles:
    @pytest.mark.parametrize(
        "filename, content, expected_already_exists, expected_write_count",
        [
            ("real.mp3", b"real audio", True, 0),
            ("placeholder.mp3", bloop_data(), False, 0),
        ],
    )
    def test_existing_files(
        self,
        fake_media: FakeMediaManager,
        filename: str,
        content: bytes,
        expected_already_exists: bool,
        expected_write_count: int,
    ) -> None:
        pathlib.Path(fake_media.dir(), filename).write_bytes(content)

        assert reserve_files([make_file_url_data(filename)]) == [
            ReservedFile(
                source=make_file_url_data(filename),
                actual_filename=filename,
                already_exists=expected_already_exists,
            )
        ]
        assert len(fake_media.write_calls) == expected_write_count

    def test_missing_file_is_reserved_with_bloop(self, fake_media: FakeMediaManager) -> None:
        filename = "missing.mp3"

        assert reserve_files([make_file_url_data(filename)]) == [
            ReservedFile(source=make_file_url_data(filename), actual_filename=filename, already_exists=False)
        ]
        assert pathlib.Path(fake_media.dir(), filename).read_bytes() == bloop_data()
        assert fake_media.write_calls == [(filename, bloop_data())]

    @pytest.mark.parametrize(
        "filename, content, expected",
        [
            ("bloop.mp3", bloop_data(), True),
            ("real.mp3", b"real audio", False),
            ("large.mp3", bloop_data() + b"large", False),
            ("missing.mp3", None, False),
        ],
    )
    def test_is_bloop_placeholder(
        self, fake_media: FakeMediaManager, filename: str, content: bytes | None, expected: bool
    ) -> None:
        if content is not None:
            pathlib.Path(fake_media.dir(), filename).write_bytes(content)

        assert is_bloop_placeholder(filename) is expected
