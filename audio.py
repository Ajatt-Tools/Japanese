# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import concurrent.futures
import io
import itertools
import os
from concurrent.futures import Future
from typing import NamedTuple
from collections.abc import Collection, Iterable, Sequence

import anki.collection
from anki.sound import SoundOrVideoTag
from anki.utils import html_to_text_line
from aqt import gui_hooks, mw, sound
from aqt.operations import QueryOp
from aqt.utils import tooltip, showWarning

from .config_view import config_view as cfg
from .helpers.audio_manager import AudioSourceManager, FileUrlData, AudioManagerException, InitResult
from .helpers.file_ops import iter_audio_cache_files
from .helpers.inflections import is_inflected
from .helpers.tokens import tokenize, ParseableToken
from .helpers.unique_files import ensure_unique_files
from .mecab_controller.kana_conv import to_hiragana, to_katakana
from .mecab_controller.mecab_controller import MecabParsedToken
from .mecab_controller.unify_readings import literal_pronunciation as pr
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


def save_files(
        futures: Collection[Future[DownloadedData]],
        play_on_finish: bool = False,
        notify_on_finish: bool = True
):
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
    if notify_on_finish is True:
        report_results(successes, fails)
    if play_on_finish is True:
        sound.av_player.play_tags([SoundOrVideoTag(filename=result.desired_filename) for result in successes])


def only_missing(col: anki.collection.Collection, files: Collection[FileUrlData]):
    """ Returns files that aren't present in the collection already. """
    return (
        file
        for file in files
        if not col.media.have(file.desired_filename)
    )


def iter_tokens(src_text: str) -> Iterable[ParseableToken]:
    for token in tokenize(html_to_text_line(src_text)):
        if isinstance(token, ParseableToken):
            yield token


def iter_mecab_variants(token: MecabParsedToken):
    yield token.headword
    if token.katakana_reading:
        yield token.katakana_reading
        yield to_hiragana(token.katakana_reading)


def format_audio_tags(hits: Collection[FileUrlData]):
    return ''.join(
        f'[sound:{hit.desired_filename}]'
        for hit in hits
    )


def sorted_files(hits: Iterable[FileUrlData]):
    """
    Sort the audio search results according to reading and pitch number
    to ensure determined order of entries.
    """
    return sorted(hits, key=lambda info: (pr(info.reading), info.pitch_number))


def exclude_inflections(hits: dict[str, list[FileUrlData]]):
    for word, word_hits in hits.items():
        hits[word] = [hit for hit in word_hits if not is_inflected(hit.word, hit.reading)]


def take_first_source(hits: dict[str, list[FileUrlData]]):
    for word, word_hits in hits.items():
        if len(word_hits) > 1:
            hits[word] = [hit for hit in word_hits if hit.source_name == word_hits[0].source_name]


class AnkiAudioSourceManager(AudioSourceManager):
    def init_audio_dictionaries(self, notify_on_finish: bool = False):
        QueryOp(
            parent=mw,
            op=lambda collection: self._init_dictionaries(),
            success=lambda result: self._after_init(result, notify_on_finish),
        ).run_in_background()

    def search_audio(
            self,
            src_text: str,
            *,
            split_morphemes: bool,
            ignore_inflections: bool,
            stop_if_one_source_has_results: bool
    ) -> list[FileUrlData]:
        """
        Search audio files (pronunciations) for words contained in search text.
        """
        hits: dict[str, list[FileUrlData]] = collections.defaultdict(list)
        src_text, src_text_reading = split_possible_furigana(html_to_text_line(src_text))

        # Try full text search.
        hits[src_text].extend(self._search_word_variants(src_text))

        # If reading was specified, erase results that don't match the reading.
        if hits[src_text] and src_text_reading:
            hits[src_text] = [hit for hit in hits[src_text] if pr(hit.reading) == pr(src_text_reading)]

        # If reading was specified, try searching by the reading only.
        if not hits[src_text] and src_text_reading:
            hits[src_text].extend(self._search_word_variants(src_text_reading))

        # Try to split the source text in various ways, trying mecab if everything fails.
        if not hits[src_text]:
            for part in dict.fromkeys(iter_tokens(src_text)):
                if files := tuple(self._search_word_variants(part)):
                    hits[part].extend(files)
                elif split_morphemes:
                    hits.update(self._parse_and_search_audio(part))

        # Filter out inflections if the user wants to.
        if ignore_inflections:
            exclude_inflections(hits)

        # Keep only items where the name of the source is equal to the name
        # of the first source that has yielded matches.
        if stop_if_one_source_has_results:
            take_first_source(hits)

        return sorted_files(ensure_unique_files(itertools.chain(*hits.values())))

    def download_tags_bg(
            self,
            hits: Sequence[FileUrlData],
            *,
            play_on_finish: bool = False,
            notify_on_finish: bool = True
    ):
        if not hits:
            return
        QueryOp(
            parent=mw,
            op=lambda col: self._download_tags(only_missing(col, hits)),
            success=lambda futures: save_files(
                futures,
                play_on_finish=play_on_finish,
                notify_on_finish=notify_on_finish,
            ),
        ).run_in_background()

    def _search_word_variants(self, src_text: str) -> Iterable[FileUrlData]:
        """
        Search word.
        If nothing is found, try searching in hiragana and katakana.
        """
        yield from self.search_word(src_text)
        yield from self.search_word(to_hiragana(src_text))
        yield from self.search_word(to_katakana(src_text))

    def _parse_and_search_audio(self, src_text: ParseableToken) -> dict[str, list[FileUrlData]]:
        hits: dict[str, list[FileUrlData]] = collections.defaultdict(list)
        for parsed in mecab_translate(src_text):
            for variant in iter_mecab_variants(parsed):
                if files := tuple(self._search_word_variants(variant)):
                    hits[parsed.headword].extend(files)
                    # If found results, break because all further results will be duplicates.
                    break
        return hits

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

    def _after_init(self, result: InitResult, notify_on_finish: bool):
        self._set_sources(result.sources)
        self._remove_old_cache_files()
        self._report_init_results(result, notify_on_finish)

    def _report_init_results(self, result: InitResult, notify_on_finish: bool):
        if result.errors:
            showWarning('\n'.join(
                f"Couldn't download audio source: {error.explanation}."
                for error in result.errors
            ))
        elif notify_on_finish and result.sources:
            stats = self.total_stats()
            tooltip(
                "<b>Initialized audio sources.</b><ul>"
                f"<li>Unique audio files: <code>{stats.unique_files}</code></li>"
                f"<li>Unique headwords: <code>{stats.unique_headwords}</code></li></ul>",
                period=5000,
            )

    def _remove_old_cache_files(self):
        known_source_files = [source.cache_path for source in self._config.iter_audio_sources()]
        for file in iter_audio_cache_files():
            if file.path not in known_source_files:
                print(f"Removing unused audio cache file: {file.name}")
                os.remove(file)


# Entry point
##########################################################################


aud_src_mgr = AnkiAudioSourceManager(cfg)
gui_hooks.main_window_did_init.append(aud_src_mgr.init_audio_dictionaries)
