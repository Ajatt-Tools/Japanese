# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import concurrent.futures
import itertools
from collections.abc import Collection, Iterable, Sequence
from concurrent.futures import Future
from typing import NamedTuple, Optional, Callable, Any

import anki.collection
from anki.utils import html_to_text_line
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.utils import tooltip, showWarning

from .config_view import config_view as cfg
from .helpers.audio_manager import (
    AudioSourceManager,
    FileUrlData,
    AudioManagerException,
    InitResult,
    AudioSourceManagerFactory,
    TotalAudioStats,
)
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


class FileSaveResults(NamedTuple):
    successes: list[DownloadedData]
    fails: list[AudioManagerException]


def save_files(
    futures: Collection[Future[DownloadedData]],
    on_finish: Optional[Callable[[FileSaveResults], Any]],
) -> FileSaveResults:
    results = FileSaveResults([], [])
    for future in futures:
        try:
            result = future.result()
        except AudioManagerException as ex:
            results.fails.append(ex)
        else:
            mw.col.media.write_data(
                desired_fname=result.desired_filename,
                data=result.data,
            )
            results.successes.append(result)
    if on_finish:
        on_finish(results)
    return results


def only_missing(col: anki.collection.Collection, files: Collection[FileUrlData]):
    """Returns files that aren't present in the collection already."""
    return (file for file in files if not col.media.have(file.desired_filename))


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
    """
    Create [sound:filename.ext] tags that Anki understands.
    """
    return cfg.audio_settings.tag_separator.join(f"[sound:{hit.desired_filename}]" for hit in hits)


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
    def search_audio(
        self,
        src_text: str,
        *,
        split_morphemes: bool,
        ignore_inflections: bool,
        stop_if_one_source_has_results: bool,
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

    def download_and_save_tags(
        self,
        hits: Sequence[FileUrlData],
        *,
        on_finish: Optional[Callable[[FileSaveResults], Any]] = None,
    ) -> None:
        """
        Download and save audio files using QueryOp.
        This method must be called from the main thread or by using mw.taskman.run_on_main().
        """

        if len(hits) < 1:
            # Sequence is empty. Nothing to do.
            return

        return QueryOp(
            parent=mw,
            op=lambda col: self._download_tags(only_missing(col, hits)),
            success=lambda futures: save_files(
                futures,
                on_finish=on_finish,
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
        """Download audio files from a remote."""

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
            self._get_file(audio_file),
        )

    def remove_unused_audio_data(self):
        user_specified_source_names = {source.name for source in self._config.iter_audio_sources()}
        source_names_in_db = set(self._db.source_names())
        sources_to_remove = source_names_in_db - user_specified_source_names
        for source_name in sources_to_remove:
            print(f"Removing unused cache data for audio source: {source_name}")
            self.db.remove_data(source_name)


class AnkiAudioSourceManagerFactory(AudioSourceManagerFactory):
    def init_sources(self, notify_on_finish: bool = False):
        QueryOp(
            parent=mw,
            op=lambda collection: self._get_sources(),
            success=lambda result: self._after_init(result, notify_on_finish),
        ).run_in_background()

    def get_statistics(self) -> TotalAudioStats:
        """
        Return statistics, running in a new session.
        """
        with self.request_new_session() as session:
            return session.total_stats()

    def _after_init(self, result: InitResult, notify_on_finish: bool):
        self._set_sources(result.sources)
        with self.request_new_session() as session:
            session.remove_unused_audio_data()
        self._report_init_results(result, notify_on_finish)

    def _report_init_results(self, result: InitResult, notify_on_finish: bool):
        if result.errors:
            showWarning("\n".join(f"Couldn't download audio source: {error.explanation}." for error in result.errors))
        elif notify_on_finish and result.sources:
            QueryOp(
                parent=mw,
                op=lambda collection: self.get_statistics(),
                success=lambda stats: tooltip(
                    "<b>Initialized audio sources.</b><ul>"
                    f"<li>Unique audio files: <code>{stats.unique_files}</code></li>"
                    f"<li>Unique headwords: <code>{stats.unique_headwords}</code></li></ul>",
                    period=5000,
                ),
            ).without_collection().run_in_background()
        print("Initialized all audio sources.")


# Entry point
##########################################################################


aud_src_mgr = AnkiAudioSourceManagerFactory(cfg, AnkiAudioSourceManager)
# react to anki's state changes
gui_hooks.profile_did_open.append(aud_src_mgr.init_sources)
