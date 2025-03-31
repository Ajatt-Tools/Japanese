# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import concurrent.futures
import itertools
from collections.abc import Collection, Iterable, Sequence
from concurrent.futures import Future
from typing import Any, Callable, NamedTuple, Optional

import anki.collection
from anki.utils import html_to_text_line
from aqt import gui_hooks, mw
from aqt.operations import QueryOp
from aqt.utils import show_warning, tooltip

from .audio_manager.abstract import (
    AnkiAudioSourceManagerABC,
    AudioSourceManagerFactoryABC,
)
from .audio_manager.audio_manager import AudioSourceManagerFactory
from .audio_manager.basic_types import (
    AudioManagerException,
    AudioSourceConfig,
    FileUrlData,
    NameUrlSet,
)
from .audio_manager.source_manager import (
    AudioSourceManager,
    InitResult,
    TotalAudioStats,
)
from .config_view import JapaneseConfig
from .config_view import config_view as cfg
from .helpers.inflections import is_inflected
from .helpers.mingle_readings import split_possible_furigana
from .helpers.sqlite3_buddy import Sqlite3Buddy
from .helpers.tokens import ParseableToken, tokenize
from .helpers.unique_files import ensure_unique_files
from .mecab_controller.kana_conv import to_hiragana, to_katakana
from .mecab_controller.mecab_controller import MecabParsedToken
from .mecab_controller.unify_readings import literal_pronunciation as pr
from .reading import mecab


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
            result: DownloadedData = future.result()
        except AudioManagerException as ex:
            results.fails.append(ex)
        else:
            assert mw, "Anki should be running."
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


def iter_mecab_variants(token: MecabParsedToken) -> Iterable[str]:
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


class AnkiAudioSourceManager(AudioSourceManager, AnkiAudioSourceManagerABC):
    _config: JapaneseConfig

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
        src_text, src_text_reading = split_possible_furigana(
            html_to_text_line(src_text), cfg.furigana.reading_separator
        )

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

        assert mw, "Anki should be running."
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
        for parsed in mecab.translate(src_text):
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
            desired_filename=audio_file.desired_filename,
            data=self._get_file(audio_file),
        )

    def remove_unused_audio_data(self):
        user_specified_source_names = frozenset(source.name for source in self._config.iter_audio_sources())
        source_names_in_db = frozenset(self._db.source_names())
        sources_to_remove = source_names_in_db - user_specified_source_names
        for source_name in sources_to_remove:
            print(f"Removing unused cache data for audio source: {source_name}")
            self.remove_data(source_name)


def describe_audio_stats(stats: TotalAudioStats) -> str:
    return (
        "<b>Initialized audio sources.</b><ul>"
        f"<li>Unique audio files: <code>{stats.unique_files}</code></li>"
        f"<li>Unique headwords: <code>{stats.unique_headwords}</code></li></ul>"
    )


def show_audio_init_result_tooltip(result: InitResult) -> None:
    if result.sources:
        assert mw, "Anki should be running."
        QueryOp(
            parent=mw,
            op=lambda collection: aud_src_mgr.get_statistics(),
            success=lambda stats: tooltip(describe_audio_stats(stats), period=5000),
        ).without_collection().run_in_background()


def report_audio_init_errors(result: InitResult) -> None:
    if result.errors:
        show_warning(
            "\n".join(f"Couldn't load audio source {error.file.url}: {error.explanation}." for error in result.errors)
        )


class AnkiAudioSourceManagerFactory:
    _config: JapaneseConfig

    def __init__(self, config: JapaneseConfig):
        self._config = config
        self._fac = AudioSourceManagerFactory(config)

    def remove_sources_from_db(
        self,
        gui_selected_sources: NameUrlSet,
        *,
        on_finish: Callable[[list[AudioSourceConfig]], Any],
    ) -> None:
        assert mw, "Anki should be running."
        QueryOp(
            parent=mw,
            op=lambda collection: self._fac.remove_selected(gui_selected_sources),
            success=lambda result: on_finish(result),
        ).without_collection().run_in_background()

    def request_new_session(self, db: Sqlite3Buddy) -> AnkiAudioSourceManager:
        """
        If tasks are being done in a different thread, prepare a new db connection
        to avoid sqlite3 throwing an instance of sqlite3.ProgrammingError.
        """
        assert mw, "Anki should be running."
        return AnkiAudioSourceManager(
            config=self._config,
            http_client=self._fac.http_client,
            db=db,
            audio_sources=self._fac.audio_sources,
        )

    def purge_everything(
        self,
        *,
        on_finish: Callable[[], Any],
    ) -> None:
        assert mw, "Anki should be running."

        def on_finish_wrapper():
            self._fac.set_sources([])
            on_finish()

        QueryOp(
            parent=mw,
            op=lambda collection: self._fac.purge_sources(),
            success=lambda result: on_finish_wrapper(),
        ).run_in_background()

    def init_sources_anki(
        self,
        *,
        on_finish: Optional[Callable[[InitResult], Any]] = None,
    ) -> None:
        assert mw, "Anki should be running."
        QueryOp(
            parent=mw,
            op=lambda collection: self._get_sources(),
            success=lambda result: self._after_init(result, on_finish),
        ).run_in_background()

    def _get_sources(self) -> InitResult:
        with Sqlite3Buddy() as db:
            session = self.request_new_session(db)
            if not session.source_config_changed():
                print("audio sources haven't changed.")
                return InitResult.did_not_run()
            else:
                return self._fac.get_sources(session)

    def get_statistics(self) -> TotalAudioStats:
        """
        Return statistics, running in a new session.
        """
        with Sqlite3Buddy() as db:
            session = self.request_new_session(db)
            return session.total_stats()

    def _remove_unused_audio_data(self) -> None:
        with Sqlite3Buddy() as db:
            session = self.request_new_session(db)
            session.remove_unused_audio_data()

    def _after_init(
        self,
        result: InitResult,
        on_finish: Optional[Callable[[InitResult], Any]] = None,
    ) -> None:
        if result.did_run:
            self._fac.set_sources(result.sources)
            self._remove_unused_audio_data()
            report_audio_init_errors(result)
            print("Initialized all audio sources.")
        if on_finish:
            on_finish(result)


# Entry point
##########################################################################


aud_src_mgr = AnkiAudioSourceManagerFactory(cfg)
# react to anki's state changes
gui_hooks.profile_did_open.append(aud_src_mgr.init_sources_anki)
