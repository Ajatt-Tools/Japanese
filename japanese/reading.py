# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import functools
from collections import OrderedDict
from collections.abc import Iterable, MutableSequence, Sequence
from typing import Optional, Union

from anki.utils import html_to_text_line
from aqt import gui_hooks

from .config_view import ReadingsDiscardMode
from .config_view import config_view as cfg
from .helpers import LONG_VOWEL_MARK
from .helpers.common_kana import adjust_to_inflection
from .helpers.mingle_readings import mingle_readings, split_possible_furigana
from .helpers.profiles import PitchOutputFormat
from .helpers.tokens import ParseableToken, Token, split_separators, tokenize
from .mecab_controller.basic_types import Inflection, PartOfSpeech
from .mecab_controller.format import format_output
from .mecab_controller.kana_conv import is_kana_str, to_hiragana
from .mecab_controller.mecab_controller import MecabController, MecabParsedToken
from .mecab_controller.unify_readings import literal_pronunciation as pr
from .mecab_controller.unify_readings import unify_repr
from .pitch_accents.acc_dict_mgr import AccentDict, AccentDictManager, FormattedEntry
from .pitch_accents.basic_types import AccDbParsedToken, PitchAccentEntry
from .pitch_accents.styles import STYLE_MAP
from .pitch_accents.svg_graphs import SvgPitchGraphMaker

# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """Map style classes to their user-configured inline versions."""
    for k, v in STYLE_MAP[cfg.pitch_accent.html_style].items():
        txt = txt.replace(k, v)
    return txt


def update_html(html_notation: str) -> str:
    html_notation = convert_to_inline_style(html_notation)
    if cfg.pitch_accent.output_hiragana:
        html_notation = to_hiragana(html_notation)
    return html_notation


@functools.lru_cache(maxsize=cfg.cache_lookups)
def mecab_translate(expr: str) -> tuple[MecabParsedToken, ...]:
    return tuple(mecab.translate(expr))


def single_word_reading(word: str) -> str:
    """
    Try to look up the reading of a single word using mecab.
    """
    if len(tokens := mecab_translate(word)) == 1 and (token := tokens[-1]).katakana_reading:
        return token.katakana_reading
    return ""


def get_pronunciations_part(expr_part: str, use_mecab: bool) -> AccentDict:
    """
    Search pitch accent info (pronunciations) for a part of expression.
    The part must be already sanitized.
    (If enabled and) if the part is not present in the accent dictionary, Mecab is used to split it further.
    """
    ret: AccentDict
    ret = AccentDict(OrderedDict())
    # Sanitize is always set to False because the part must be already sanitized.
    ret.update(get_pronunciations(expr_part, sanitize=False, recurse=False))

    # Only if lookups were not successful, we try splitting with Mecab
    if not ret and use_mecab is True:
        for out in mecab_translate(expr_part):
            # Avoid infinite recursion by saying that we should not try
            # Mecab again if we do not find any matches for this sub-expression.
            ret.update(get_pronunciations(out.headword, sanitize=False, recurse=False))

            # If everything failed, try katakana lookups.
            # Katakana lookups are possible because of the additional key in the pitch accents dictionary.
            # If the word was in conjugated form, this lookup will also fail.
            if out.headword not in ret and out.katakana_reading and cfg.pitch_accent.kana_lookups is True:
                ret.update(get_pronunciations(out.katakana_reading, sanitize=False, recurse=False))
    return ret


@functools.lru_cache(maxsize=cfg.cache_lookups)
def get_pronunciations(expr: str, sanitize: bool = True, recurse: bool = True, use_mecab: bool = True) -> AccentDict:
    """
    Search pitch accent info (pronunciations) for a particular expression.

    Returns a dictionary mapping the expression (or sub-expressions contained in the expression)
    to a list of html-styled pronunciations.
    """

    ret: AccentDict
    ret = AccentDict(OrderedDict())

    # Sanitize input
    if sanitize:
        expr = html_to_text_line(expr)

    # Handle furigana, if present.
    expr, expr_reading = split_possible_furigana(expr, cfg.furigana.reading_separator)

    # Skip empty strings and user-specified blocklisted words
    if not expr or cfg.pitch_accent.is_blocklisted(expr):
        return ret

    # Look up the main expression.
    if lookup_main := acc_dict.lookup(expr):
        ret.setdefault(expr, []).extend(
            entry
            for entry in lookup_main
            # if there's furigana, and it doesn't match the entry, skip.
            if not expr_reading or pr(entry.katakana_reading) == pr(expr_reading)
        )

    # If there's furigana, e.g. when using the VocabFurigana field as the source,
    # or if the kana reading of the full expression can be sourced from mecab,
    # and the user wants to perform kana lookups, then try the reading.
    if not ret and cfg.pitch_accent.kana_lookups:
        expr_reading = expr_reading or single_word_reading(expr)
        if expr_reading and (lookup_reading := acc_dict.lookup(expr_reading)):
            ret.setdefault(expr, []).extend(lookup_reading)

    # Try to split the expression in various ways (punctuation, whitespace, etc.),
    # and check if any of those brings results.
    if not ret and recurse:
        for section in split_separators(expr):
            ret.update(get_pronunciations_part(section, use_mecab=use_mecab))
    return ret


def iter_accents(word: str) -> Iterable[FormattedEntry]:
    if word in (accents := get_pronunciations(word, recurse=False)):
        yield from accents[word]


def get_notation(entry: FormattedEntry, mode: PitchOutputFormat) -> str:
    if mode == PitchOutputFormat.html:
        return update_html(entry.html_notation)
    elif mode == PitchOutputFormat.number:
        return entry.pitch_number
    elif mode == PitchOutputFormat.html_and_number:
        return update_html(f"{entry.html_notation} {entry.pitch_number_html}")
    elif mode == PitchOutputFormat.svg:
        return svg_graph_maker.make_graph(entry)
    raise RuntimeError("Unreachable.")


def sort_entries(entries: Sequence[FormattedEntry]) -> Sequence[FormattedEntry]:
    return sorted(entries, key=lambda entry: (entry.katakana_reading, entry.pitch_number))


def entries_to_html(
    entries: Sequence[FormattedEntry],
    output_format: PitchOutputFormat,
    max_results: Optional[int],
) -> Sequence[str]:
    """
    Convert entries to HTML, sort and remove duplicates.
    """
    return discard_extra_readings(
        tuple(dict.fromkeys(get_notation(entry, output_format) for entry in sort_entries(entries))),
        max_results=max_results or cfg.pitch_accent.maximum_results,
        discard_mode=cfg.pitch_accent.discard_mode,
    )


def format_pronunciations(
    pronunciations: AccentDict,
    output_format: PitchOutputFormat = PitchOutputFormat.html,
    sep_single: str = "・",
    sep_multi: str = "、",
    expr_sep: Optional[str] = None,
    max_results: Optional[int] = None,
) -> str:
    ordered_dict = OrderedDict()
    for word, entries in pronunciations.items():
        if entries_html := entries_to_html(entries, output_format, max_results=max_results):
            ordered_dict[word] = sep_single.join(entries_html)

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join(f"{word}{expr_sep}{entries}" for word, entries in ordered_dict.items() if word and entries)
    else:
        txt = sep_multi.join(ordered_dict.values())

    return txt


def format_furigana_readings(word: str, hiragana_readings: Sequence[str]) -> str:
    """
    Pack all readings into this format: "word[reading<sep>reading, ...]suffix".
    If there are too many readings to pack, discard all but the first.
    """
    furigana_readings = [
        format_output(
            word,
            reading=(reading if cfg.furigana.prefer_literal_pronunciation is False else unify_repr(reading)),
        )
        for reading in hiragana_readings
        if reading
    ]
    if 1 < len(furigana_readings):
        return mingle_readings(furigana_readings, sep=cfg.furigana.reading_separator)
    else:
        return furigana_readings[0]


def format_hiragana_readings(readings: Sequence[str]) -> str:
    """Discard kanji and format the readings as hiragana."""
    if 1 < len(readings):
        return f"({cfg.furigana.reading_separator.join(map(to_hiragana, readings))})"
    else:
        return to_hiragana(readings[0])


def discard_extra_readings(
    readings: Sequence[str],
    *,
    max_results: int,
    discard_mode: ReadingsDiscardMode,
) -> Sequence[str]:
    """Depending on the settings, if there are too many readings, discard some or all but the first."""
    if max_results <= 0 or len(readings) <= max_results:
        return readings
    elif discard_mode == ReadingsDiscardMode.discard_extra:
        return readings[:max_results]
    elif discard_mode == ReadingsDiscardMode.keep_first:
        return readings[:1]
    elif discard_mode == ReadingsDiscardMode.discard_all:
        return []
    else:
        raise ValueError(f"No handler for mode {discard_mode}.")


def try_lookup_full_text(text: str) -> Iterable[AccDbParsedToken]:
    """
    Try looking up whole text in the accent db.
    Avoids calling mecab when the text contains one word in dictionary form
    or multiple words in dictionary form separated by punctuation.
    """
    word: str
    entries: Sequence[FormattedEntry]

    if cfg.furigana.can_lookup_in_db(text) and (results := get_pronunciations(text, recurse=False)):
        for word, entries in results.items():
            yield AccDbParsedToken(
                headword=word,
                word=word,
                part_of_speech=PartOfSpeech.unknown,
                inflection_type=Inflection.dictionary_form,
                katakana_reading=None,
                headword_accents=[PitchAccentEntry.from_formatted(entry) for entry in entries],
            )


def unique_readings(readings: Iterable[str]) -> Sequence[str]:
    """
    Return a list of readings without repetitions.
    """

    def sorted_readings() -> Sequence[str]:
        """
        Sort readings according to the user's preferences.
        The long vowel symbol is used to identify readings that resemble literal pronunciation.
        """
        return sorted(
            readings,
            key=(lambda reading: LONG_VOWEL_MARK in reading),
            reverse=(not cfg.furigana.prefer_literal_pronunciation),
        )

    return list({pr(reading): reading for reading in sorted_readings()}.values())


def all_hiragana_readings(token: AccDbParsedToken) -> Iterable[str]:
    """
    Yield all possible hiragana readings for the word, e.g. [そそぐ, すすぐ, ゆすぐ].
    """
    if token.katakana_reading:
        yield to_hiragana(token.katakana_reading)
    for entry in token.headword_accents:
        yield adjust_to_inflection(
            raw_word=token.word,
            headword=token.headword,
            headword_reading=to_hiragana(entry.katakana_reading),
        )


def format_acc_db_result(out: AccDbParsedToken, full_hiragana: bool = False) -> str:
    """
    Given a word and a list of its readings, produce the appropriate furigana or kana output.
    """
    if is_kana_str(out.word) or cfg.furigana.is_blocklisted(out.word):
        return out.word

    readings = discard_extra_readings(
        readings=unique_readings(all_hiragana_readings(out)),
        max_results=cfg.furigana.maximum_results,
        discard_mode=cfg.furigana.discard_mode,
    )

    if not readings:
        return out.word

    if full_hiragana:
        return format_hiragana_readings(readings)

    return format_furigana_readings(out.word, readings)


def append_accents(token: MecabParsedToken) -> AccDbParsedToken:
    return AccDbParsedToken(
        **dataclasses.asdict(token),
        headword_accents=[PitchAccentEntry.from_formatted(entry) for entry in iter_accents(token.headword)],
    )


def format_parsed_tokens(
    tokens: Sequence[Union[AccDbParsedToken, Token]],
    full_hiragana: bool = False,
) -> Iterable[str]:
    for token in tokens:
        if isinstance(token, AccDbParsedToken):
            yield format_acc_db_result(token, full_hiragana=full_hiragana)
        elif isinstance(token, str):
            yield token
        else:
            raise ValueError(f"Invalid type: {type(token)}")


def generate_furigana(src_text: str, split_morphemes: bool = True, full_hiragana: bool = False) -> str:
    substrings: MutableSequence[Union[AccDbParsedToken, Token]] = []
    for token in tokenize(src_text):
        if not isinstance(token, ParseableToken) or is_kana_str(token):
            # Skip tokens that can't be parsed (non-japanese text).
            # Skip full-kana tokens (no furigana is needed).
            substrings.append(token)
        elif acc_db_result := tuple(try_lookup_full_text(token)):
            # If full text search succeeded, continue.
            substrings.extend(acc_db_result)
        elif split_morphemes is True:
            # Split with mecab, format furigana for each word.
            substrings.extend(append_accents(out) for out in mecab_translate(token))
        elif (out := mecab_translate(token)) and out[0].word == token:
            # If the user doesn't want to split morphemes, still try to find the reading using mecab
            # but abort if mecab outputs more than one word.
            substrings.append(append_accents(out[0]))
        else:
            # Add the string as is, without furigana.
            substrings.append(token)
    return "".join(format_parsed_tokens(substrings, full_hiragana)).strip()


# Entry point
##########################################################################


mecab = MecabController(verbose=True)
svg_graph_maker = SvgPitchGraphMaker(options=cfg.svg_graphs)
acc_dict = AccentDictManager()
gui_hooks.main_window_did_init.append(acc_dict.reload_from_disk)
