# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import io
from collections.abc import Collection
from concurrent.futures import Future
from typing import Any, Callable, NamedTuple, Optional

from aqt import mw

from .basic_types import AudioManagerException, FileUrlData


class DownloadedData(NamedTuple):
    desired_filename: str
    data: bytes


class FileSaveResults(NamedTuple):
    successes: list[DownloadedData]
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


def format_report_successes_msg(successes: list[DownloadedData]) -> str:
    buffer = io.StringIO()
    buffer.write(f"<b>Added {len(successes)} files to the collection.</b><ol>")
    for file in successes:
        buffer.write(f"<li>{file.desired_filename}</li>")
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


def save_files(
    futures: Collection[Future[DownloadedData]],
    on_finish: Optional[Callable[[FileSaveResults], Any]],
) -> FileSaveResults:
    results = FileSaveResults([], [])
    for future in futures:
        try:
            result: DownloadedData = future.result()
        except AudioManagerException as ex:
            results.fails.append(ex)
        else:
            assert mw, "Anki should be running."
            # TODO: write_data() returns possibly-renamed filename. React if file gets renamed.
            mw.col.media.write_data(
                desired_fname=result.desired_filename,
                data=result.data,
            )
            results.successes.append(result)
    if on_finish:
        on_finish(results)
    return results
