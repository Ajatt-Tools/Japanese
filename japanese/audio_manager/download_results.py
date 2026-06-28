# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import io
import os
import pathlib
from collections.abc import Callable, Collection, Iterable, Sequence
from concurrent.futures import Future
from typing import Any, NamedTuple, Optional

from aqt import mw

from .basic_types import AudioManagerException, FileUrlData

# A short dummy audio file used to pre-reserve filenames in the media collection.
# When a download fails, the dummy file remains and the user hears a "bloop" sound,
# which is an explicit audible signal that the download failed.
BLOOP_FILE = pathlib.Path(__file__).parent.joinpath("data", "bloop.ogg")
assert BLOOP_FILE.is_file(), "add-on must contain the bloop file to work correctly."


class ReservedFile(NamedTuple):
    """A file whose filename has been pre-reserved in the Anki media collection.

    The dummy file (bloop.ogg) is written to the collection so that write_data()
    can return the actual (normalized, collision-resolved) filename before the
    real audio is downloaded. The real audio data overwrites the dummy later.
    """

    source: FileUrlData
    actual_filename: str
    already_exists: bool


def only_missing(reserved_files: Iterable[ReservedFile]) -> Iterable[ReservedFile]:
    """Returns files that aren't present in the collection already."""
    yield from (file for file in reserved_files if not file.already_exists)


class DownloadedData(NamedTuple):
    reserved: ReservedFile
    data: bytes


class FileSaveResults(NamedTuple):
    successes: list[ReservedFile]
    fails: list[AudioManagerException]


def calc_tooltip_offset(n_lines: int) -> int:
    """
    For longer messages, increase the tooltip offset 🪄🪄🪄.
    """
    return 80 + 18 * n_lines


def format_report_errors_msg(fails: list[AudioManagerException]) -> str:
    buffer = io.StringIO()
    buffer.write(f"<b>Failed {len(fails)} files.</b><ol>")
    for fail in fails:
        if isinstance(fail.file, FileUrlData):
            buffer.write(f"<li>{fail.file.desired_filename}: {fail.describe_short()}</li>")
    buffer.write("</ol>")
    return buffer.getvalue()


def format_report_successes_msg(successes: list[ReservedFile]) -> str:
    buffer = io.StringIO()
    buffer.write(f"<b>Added {len(successes)} files to the collection.</b><ol>")
    for file in successes:
        buffer.write(f"<li>{file.actual_filename}</li>")
    buffer.write("</ol>")
    return buffer.getvalue()


def format_report_results_msg(r: FileSaveResults) -> str:
    """
    Make text for a tooltip with audio download results.
    """
    buffer = io.StringIO()
    if r.successes:
        buffer.write(format_report_successes_msg(r.successes))
    if r.fails:
        buffer.write(format_report_errors_msg(r.fails))
    return buffer.getvalue()


def reserve_files(hits: Sequence[FileUrlData]) -> list[ReservedFile]:
    """Pre-reserve filenames in the media collection by writing a dummy file.

    For each hit, either the file already exists (actual_filename = desired_filename),
    or write_data() is called with dummy audio to reserve the normalized name.
    Must be called from the main thread.
    """
    assert mw, "Anki should be running."
    assert mw.col, "Collection should be open."

    bloop_data = BLOOP_FILE.read_bytes()
    reserved: list[ReservedFile] = []
    for hit in hits:
        if mw.col.media.have(hit.desired_filename):
            reserved.append(ReservedFile(source=hit, actual_filename=hit.desired_filename, already_exists=True))
        else:
            actual_filename = mw.col.media.write_data(desired_fname=hit.desired_filename, data=bloop_data)
            reserved.append(ReservedFile(source=hit, actual_filename=actual_filename, already_exists=False))
    return reserved


def save_files(
    futures: Collection[Future[DownloadedData]],
    on_finish: Callable[[FileSaveResults], Any] | None,
) -> FileSaveResults:
    """Overwrite pre-reserved dummy files with the downloaded audio data.

    Each future's DownloadedData carries its own ReservedFile, so no external
    mapping is needed. On success, the real audio bytes are written directly
    to the reserved path, replacing the dummy bloop.ogg content. On failure,
    the dummy file is left as-is; the user will hear a "bloop" when playing,
    signaling the failed download.
    """
    assert mw, "Anki should be running."
    assert mw.col, "Collection should be open."

    results = FileSaveResults([], [])
    for future in futures:
        try:
            result: DownloadedData = future.result()
        except AudioManagerException as ex:
            results.fails.append(ex)
        else:
            # Overwrite the dummy file with the real audio data.
            file_path = os.path.join(mw.col.media.dir(), result.reserved.actual_filename)
            with open(file_path, "wb") as f:
                f.write(result.data)
            results.successes.append(result.reserved)
    if on_finish:
        on_finish(results)
    return results
