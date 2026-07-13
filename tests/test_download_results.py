# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
from concurrent.futures import Future

import pytest

import japanese.audio_manager.download_results as download_results
from japanese.audio_manager.basic_types import AudioManagerException, FileUrlData
from japanese.audio_manager.download_results import (
    BLOOP_FILE,
    DownloadedData,
    FileSaveResults,
    ReservedFile,
    bloop_data,
    calc_tooltip_offset,
    is_bloop_placeholder,
    only_missing,
    reserve_files,
    save_files,
)


class FakeMediaManager:
    """Minimal media manager for testing reservation behavior."""

    def __init__(self, media_dir: str) -> None:
        self._media_dir = media_dir
        self.write_calls: list[tuple[str, bytes]] = []
        self.actual_filenames: dict[str, str] = {}

    def dir(self) -> str:
        """Return the fake collection media directory."""
        return self._media_dir

    def have(self, filename: str) -> bool:
        """Return True if a fake media file exists."""
        return (pathlib.Path(self._media_dir) / filename).exists()

    def write_data(self, desired_fname: str, data: bytes) -> str:
        """Write data using an optional normalized filename override."""
        self.write_calls.append((desired_fname, data))
        actual_fname = self.actual_filenames.get(desired_fname, desired_fname)
        pathlib.Path(self._media_dir, actual_fname).write_bytes(data)
        return actual_fname


class FakeCollection:
    """Minimal collection wrapper exposing a media manager."""

    def __init__(self, media: FakeMediaManager) -> None:
        self.media = media


class FakeMainWindow:
    """Minimal main-window wrapper exposing an Anki collection."""

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
    @pytest.mark.parametrize(
        "check_result",
        [
            BLOOP_FILE.is_file(),
            BLOOP_FILE.stat().st_size > 0,
        ],
    )
    def test_bloop_file_is_usable(self, check_result: bool) -> None:
        """The bundled placeholder audio file exists and is nonempty."""
        assert check_result is True


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

    @pytest.mark.parametrize("filename", ["missing.mp3"])
    def test_missing_file_is_reserved_with_bloop(self, fake_media: FakeMediaManager, filename: str) -> None:
        """A missing target filename is pre-reserved with the bloop placeholder."""
        assert reserve_files([make_file_url_data(filename)]) == [
            ReservedFile(source=make_file_url_data(filename), actual_filename=filename, already_exists=False)
        ]
        assert pathlib.Path(fake_media.dir(), filename).read_bytes() == bloop_data()
        assert fake_media.write_calls == [(filename, bloop_data())]

    @pytest.mark.parametrize("desired_filename, actual_filename", [("missing.mp3", "missing (1).mp3")])
    def test_missing_file_uses_actual_filename_from_media_manager(
        self, fake_media: FakeMediaManager, desired_filename: str, actual_filename: str
    ) -> None:
        """The reserved filename tracks Anki's normalized or collision-resolved filename."""
        fake_media.actual_filenames[desired_filename] = actual_filename

        assert reserve_files([make_file_url_data(desired_filename)]) == [
            ReservedFile(
                source=make_file_url_data(desired_filename), actual_filename=actual_filename, already_exists=False
            )
        ]
        assert pathlib.Path(fake_media.dir(), actual_filename).read_bytes() == bloop_data()
        assert fake_media.write_calls == [(desired_filename, bloop_data())]

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


class TestSaveFiles:
    @pytest.mark.parametrize("actual_filename, downloaded_data", [("reserved.mp3", b"downloaded audio")])
    def test_success_overwrites_placeholder(
        self, fake_media: FakeMediaManager, actual_filename: str, downloaded_data: bytes
    ) -> None:
        """Successful downloads overwrite the placeholder and report a success."""
        pathlib.Path(fake_media.dir(), actual_filename).write_bytes(bloop_data())
        future: Future[DownloadedData] = Future()
        reserved = make_reserved(actual_filename=actual_filename)
        future.set_result(DownloadedData(reserved=reserved, data=downloaded_data))

        assert save_files([future], on_finish=None) == FileSaveResults(successes=[reserved], fails=[])
        assert pathlib.Path(fake_media.dir(), actual_filename).read_bytes() == downloaded_data

    @pytest.mark.parametrize("actual_filename", ["reserved.mp3"])
    def test_failure_keeps_placeholder(self, fake_media: FakeMediaManager, actual_filename: str) -> None:
        """Failed downloads leave the placeholder in place and report a failure."""
        pathlib.Path(fake_media.dir(), actual_filename).write_bytes(bloop_data())
        future: Future[DownloadedData] = Future()
        exception = AudioManagerException(
            file=make_file_url_data(actual_filename),
            explanation="failed",
            exception=RuntimeError("failed"),
        )
        future.set_exception(exception)

        assert save_files([future], on_finish=None) == FileSaveResults(successes=[], fails=[exception])
        assert pathlib.Path(fake_media.dir(), actual_filename).read_bytes() == bloop_data()

    @pytest.mark.parametrize("actual_filename, downloaded_data", [("reserved.mp3", b"downloaded audio")])
    def test_on_finish_receives_results(
        self, fake_media: FakeMediaManager, actual_filename: str, downloaded_data: bytes
    ) -> None:
        """The optional callback receives the same results returned by save_files."""
        future: Future[DownloadedData] = Future()
        reserved = make_reserved(actual_filename=actual_filename)
        future.set_result(DownloadedData(reserved=reserved, data=downloaded_data))
        callback_results: list[FileSaveResults] = []

        assert save_files([future], on_finish=callback_results.append) == FileSaveResults(
            successes=[reserved], fails=[]
        )
        assert callback_results == [FileSaveResults(successes=[reserved], fails=[])]
