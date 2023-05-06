# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import concurrent.futures
import io
import os
from concurrent.futures import Future
from typing import Collection, NamedTuple, Iterable

import anki.collection
from anki.utils import html_to_text_line
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.utils import tooltip, showWarning

from .config_view import config_view as cfg
from .helpers.audio_manager import AudioSourceManager, FileUrlData, AudioManagerException, InitResult
from .helpers.file_ops import user_files_dir
from .helpers.tokens import tokenize, ParseableToken
from .helpers.unify_readings import literal_pronunciation as pr
from .mecab_controller import to_hiragana, to_katakana
from .mecab_controller.mecab_controller import MecabParsedToken
from .reading import mecab_translate, split_possible_furigana


class DownloadedData(NamedTuple):
    desired_filename: str
    data: bytes


def report_results(successes: list[DownloadedData], fails: list[AudioManagerException]):
    txt = io.StringIO()
    if successes:
        txt.write(f"<b>Added {len(successes)} files to the collection.</b><ol>")
        txt.write(''.join(f"<li>{file.desired_filename}</li>" for file in successes))
        txt.write("</ol>")
    if fails:
        txt.write(f"<b>Failed {len(fails)} files.</b><ol>")
        txt.write(''.join(f"<li>{fail.file.desired_filename}: {fail.describe_short()}</li>" for fail in fails))
        txt.write("</ol>")
    if txt := txt.getvalue():
        return tooltip(txt, period=7000, y_offset=80 + 18 * (len(successes) + len(fails)))


def save_files(futures: Collection[Future[DownloadedData]]):
    successes, fails = [], []
    for future in futures:
        try:
            result = future.result()
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


def iter_tokens(src_text: str) -> Iterable[ParseableToken]:
    for token in tokenize(html_to_text_line(src_text), counters=cfg.furigana.counters):
        if isinstance(token, ParseableToken):
            yield token


def iter_parsed_variants(token: MecabParsedToken):
    yield token.headword
    if token.katakana_reading:
        yield token.katakana_reading
        yield to_hiragana(token.katakana_reading)


def format_audio_tags(hits: Collection[FileUrlData]):
    return ''.join(
        f'[sound:{hit.desired_filename}]'
        for hit in hits
    )


def is_audio_cache_file(file: os.DirEntry):
    return file.name.startswith("audio_source_") and file.name.endswith(".pickle")


class AnkiAudioSourceManager(AudioSourceManager):
    def init_audio_dictionaries(self):
        QueryOp(
            parent=mw,
            op=lambda collection: self._init_dictionaries(),
            success=lambda result: self._after_init(result),
        ).run_in_background()

    def search_audio(self, src_text: str, split_morphemes: bool) -> list[FileUrlData]:
        src_text, src_text_reading = split_possible_furigana(html_to_text_line(src_text))
        if hits := self._search_word_variants(src_text):
            # If full text search succeeded, exit.
            # If reading is present, erase results that don't match the reading.
            return (
                hits
                if not src_text_reading
                else [hit for hit in hits if pr(hit.reading) == pr(src_text_reading)]
            )
        if src_text_reading and (hits := self._search_word_variants(src_text_reading)):
            # If there are results for reading, exit.
            return hits
        for part in dict.fromkeys(iter_tokens(src_text)):
            if files := self._search_word_variants(part):
                hits.extend(files)
            elif split_morphemes:
                hits.extend(self._parse_and_search_audio(part))
        return hits

    def download_tags_bg(self, hits: Collection[FileUrlData]):
        if not hits:
            return
        QueryOp(
            parent=mw,
            op=lambda col: self._download_tags(only_missing(col, hits)),
            success=lambda futures: save_files(futures)
        ).run_in_background()

    def _search_word_sorted(self, src_text: str):
        """
        Search word and sort the results according to reading and pitch number
        to ensure determined order of entries.
        """
        return sorted(
            self.search_word(src_text),
            key=lambda info: (info.reading, info.pitch_number)
        )

    def _search_word_variants(self, src_text: str):
        """
        Search word.
        If nothing is found, try searching in hiragana and katakana.
        """
        return (
                self._search_word_sorted(src_text)
                or self._search_word_sorted(to_hiragana(src_text))
                or self._search_word_sorted(to_katakana(src_text))
        )

    def _parse_and_search_audio(self, src_text: ParseableToken) -> Iterable[FileUrlData]:
        for parsed in mecab_translate(src_text):
            for variant in iter_parsed_variants(parsed):
                if files := self._search_word_sorted(variant):
                    yield from files
                    # If found results, break because all further results will be duplicates.
                    break

    def _download_tags(self, hits: Iterable[FileUrlData]) -> list[Future[DownloadedData]]:
        """ Download audio files from a remote. """

        futures, results = [], []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for audio_file in hits:
                futures.append(executor.submit(self._download_tag, audio_file=audio_file))
            for future in concurrent.futures.as_completed(futures):
                results.append(future)
        return results

    def _download_tag(self, audio_file: FileUrlData) -> DownloadedData:
        return DownloadedData(
            audio_file.desired_filename,
            self.get_file(audio_file),
        )

    def _after_init(self, result: InitResult):
        self._set_sources(result.sources)
        self._remove_old_cache_files()
        if result.errors:
            showWarning('\n'.join(
                f"Couldn't download audio source: {error.explanation}."
                for error in result.errors
            ))

    def _remove_old_cache_files(self):
        known_source_files = [source.cache_path for source in self._config.iter_audio_sources()]
        for file in os.scandir(user_files_dir()):
            if is_audio_cache_file(file) and file.path not in known_source_files:
                print(f"Removing unused audio cache file: {file.name}")
                os.remove(file)


# Entry point
##########################################################################


aud_src_mgr = AnkiAudioSourceManager(cfg)
gui_hooks.main_window_did_init.append(aud_src_mgr.init_audio_dictionaries)
