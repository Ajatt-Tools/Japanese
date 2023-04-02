# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import concurrent.futures
from concurrent.futures import Future
from typing import Collection, NamedTuple, Iterable

import anki.collection
from anki.utils import html_to_text_line
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.utils import tooltip, show_warning

from .config_view import config_view as cfg
from .helpers.audio_manager import AudioSourceManager, FileUrlData, AudioManagerException, InitResult


class DownloadedData(NamedTuple):
    desired_filename: str
    data: bytes


def download_tag(audio_file: FileUrlData):
    return DownloadedData(
        audio_file.desired_filename,
        aud_src_mgr.get_file(audio_file),
    )


def download_tags(hits: Iterable[FileUrlData]) -> list[Future]:
    """ Download audio files from a remote. """

    futures, results = [], []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for audio_file in hits:
            futures.append(executor.submit(download_tag, audio_file=audio_file))
        for future in concurrent.futures.as_completed(futures):
            results.append(future)
    return results


def report_results(successes: list[DownloadedData], fails: list[AudioManagerException]):
    if not successes and not fails:
        return

    txt = (
            f"<b>Added {len(successes)} files to the collection.</b><ol>"
            + ''.join(f"<li>{file.desired_filename}</li>" for file in successes)
            + "</ol>"
    )
    if fails:
        txt += (
                f"<b>Failed {len(fails)} files.</b><ol>"
                + ''.join(f"<li>{file.file.desired_filename}: {file.describe_short()}</li>" for file in fails)
                + "</ol>"
        )
    return tooltip(txt, period=7000)


def save_files(futures: Collection[Future]):
    successes, fails = [], []
    for future in futures:
        try:
            result: DownloadedData = future.result()
        except AudioManagerException as ex:
            fails.append(ex)
        else:
            mw.col.media.write_data(
                desired_fname=result.desired_filename,
                data=result.data,
            )
            successes.append(result)
    report_results(successes, fails)


def only_missing(col: anki.collection.Collection, files: Collection[FileUrlData]):
    """ Returns files that aren't present in the collection already. """
    return (
        file
        for file in files
        if not col.media.have(file.desired_filename)
    )


def download_tags_bg(hits: Collection[FileUrlData]):
    if not hits:
        return
    QueryOp(
        parent=mw,
        op=lambda col: download_tags(only_missing(col, hits)),
        success=lambda futures: save_files(futures)
    ).run_in_background()


def search_audio(src_text: str, split_morphemes: bool) -> list[FileUrlData]:
    hits = []
    # TODO split morphemes if requested
    for part in html_to_text_line(src_text).strip().split():
        for audio_file in aud_src_mgr.search_word(part):
            hits.append(audio_file)
    return hits


def format_audio_tags(hits: Collection[FileUrlData]):
    return ''.join(
        f'[sound:{hit.desired_filename}]'
        for hit in hits
    )


class AnkiAudioSourceManager(AudioSourceManager):
    def init_audio_dictionaries(self):
        QueryOp(
            parent=mw,
            op=lambda collection: self.init_dictionaries(),
            success=lambda result: self._after_init(result),
        ).run_in_background()

    def _after_init(self, result: InitResult):
        self.set_sources(result.sources)
        self.remove_old_cache_files()
        if result.errors:
            show_warning('\n'.join(
                f"Couldn't download audio source: {error.explanation}."
                for error in result.errors
            ))


# Entry point
##########################################################################


aud_src_mgr = AnkiAudioSourceManager(cfg)
gui_hooks.main_window_did_init.append(aud_src_mgr.init_audio_dictionaries)
