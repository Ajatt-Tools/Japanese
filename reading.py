# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import itertools
from collections import OrderedDict
from typing import Tuple, Optional, List, Union

from anki.utils import html_to_text_line

from .config_view import config_view as cfg, ReadingsDiscardMode
from .database import AccentDict, FormattedEntry, AccentDictManager
from .helpers import *
from .helpers.common_kana import adjust_reading
from .helpers.mingle_readings import mingle_readings, word_reading, strip_non_jp_furigana
from .helpers.profiles import PitchOutputFormat
from .helpers.tokens import tokenize, split_separators, ParseableToken, clean_furigana, Token
from .helpers.unify_readings import unify_repr
from .mecab_controller import MecabController
from .mecab_controller import format_output, is_kana_str
from .mecab_controller import to_hiragana, to_katakana
from .mecab_controller.mecab_controller import MecabParsedToken


# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """ Map style classes to their user-configured inline versions. """

    for k, v in cfg.styles.items():
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


def lookup_expr_variants(expr: str) -> Iterable[FormattedEntry]:
    """Look up various forms of expr in accent db."""
    return dict.fromkeys(itertools.chain(*(
        acc_dict[variant]
        for variant in (expr, to_katakana(expr), to_hiragana(expr))
        if variant in acc_dict
    ))).keys()


@functools.lru_cache(maxsize=cfg.cache_lookups)
def get_pronunciations(expr: str, sanitize: bool = True, recurse: bool = True, use_mecab: bool = True) -> AccentDict:
    """
    Search pronunciations for a particular expression.

    Returns a dictionary mapping the expression (or sub-expressions contained in the expression)
    to a list of html-styled pronunciations.
    """

    ret = OrderedDict()

    # Sanitize input
    if sanitize:
        expr = html_to_text_line(expr)
        sanitize = False

    # Sometimes furigana notation is being used by the users to distinguish otherwise duplicate notes.
    # E.g., テスト[1], テスト[2]
    expr = strip_non_jp_furigana(expr)

    # If the expression contains furigana, split it.
    expr, expr_reading = word_reading(expr)
    expr, expr_reading = clean_furigana(expr), clean_furigana(expr_reading)

    # Skip empty strings and user-specified blocklisted words
    if not expr or cfg.pitch_accent.is_blocklisted(expr):
        return ret

    # If there are numbers or multiple readings present, ignore all of them.
    if expr_reading and (expr_reading.isnumeric() or cfg.furigana.reading_separator in expr_reading):
        expr_reading = ''

    # Look up the main expression.
    if lookup_main := lookup_expr_variants(expr):
        ret.setdefault(expr, []).extend(
            entry
            for entry in lookup_main
            # if there's furigana, and it doesn't match the entry, skip.
            if not expr_reading or to_katakana(entry.katakana_reading) == to_katakana(expr_reading)
        )

    # If there's furigana, e.g. when using the VocabFurigana field as the source,
    # and the user wants to perform kana lookups,
    # try the reading.
    if not ret and expr_reading and cfg.pitch_accent.kana_lookups:
        if lookup_reading := lookup_expr_variants(expr_reading):
            ret.setdefault(expr_reading, []).extend(lookup_reading)

    # Try to split the expression in various ways (punctuation, whitespace, etc.),
    # and check if any of those brings results.
    if not ret and recurse:
        if len(split_expr := split_separators(expr)) > 1:
            for section in split_expr:
                ret.update(get_pronunciations(section, sanitize, recurse=False))

        # Only if lookups were not successful, we try splitting with Mecab
        if not ret and use_mecab is True:
            for out in mecab_translate(expr):
                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-expression.
                ret.update(get_pronunciations(out.headword, sanitize, recurse=False))

                # If everything failed, try katakana lookups.
                # Katakana lookups are possible because of the additional key in the database.
                # If the word was in conjugated form, this lookup will also fail.
                if (
                        out.headword not in ret
                        and out.katakana_reading
                        and cfg.pitch_accent.kana_lookups is True
                ):
                    ret.update(get_pronunciations(out.katakana_reading, sanitize, recurse=False))

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
        return update_html(f'{entry.html_notation} {entry.pitch_number_html}')
    raise Exception("Unreachable.")


def format_pronunciations(
        pronunciations: AccentDict,
        output_format: PitchOutputFormat = PitchOutputFormat.html,
        sep_single: str = "・",
        sep_multi: str = "、",
        expr_sep: str = None,
) -> str:
    ordered_dict = OrderedDict()
    for word, entries in pronunciations.items():
        entries = list(dict.fromkeys(get_notation(entry, output_format) for entry in entries).keys())
        entries = discard_extra_readings(entries, cfg.pitch_accent.maximum_results, cfg.pitch_accent.discard_mode)
        if entries:
            ordered_dict[word] = sep_single.join(entries)

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join(f"{word}{expr_sep}{entries}" for word, entries in ordered_dict.items() if word and entries)
    else:
        txt = sep_multi.join(ordered_dict.values())

    return txt


def sorted_accents(headword: str) -> list[FormattedEntry]:
    return sorted(
        iter_accents(headword),
        key=lambda e: LONG_VOWEL_MARK in e.katakana_reading,
        reverse=cfg.furigana.prefer_literal_pronunciation
    )


def iter_possible_readings(out: MecabParsedToken) -> Iterable[str]:
    """
    Return all possible hiragana readings for the word, e.g. [そそぐ, すすぐ, ゆすぐ].
    If the user doesn't want to look up readings in the database,
    return back the one reading contained in the parsed token, which may be empty.
    """
    readings = {}

    if out.katakana_reading:
        readings.setdefault(
            unify_repr(to_hiragana(out.katakana_reading)),
            to_hiragana(out.katakana_reading),
        )

    if cfg.furigana.can_lookup_in_db(out.headword):
        for entry in sorted_accents(out.headword):
            reading = adjust_reading(out.word, out.headword, to_hiragana(entry.katakana_reading))
            readings.setdefault(unify_repr(reading), reading)

    return readings.values()


def format_furigana_readings(word: str, hiragana_readings: list[str]) -> str:
    """
    Pack all readings into this format: "word[reading<sep>reading, ...]suffix".
    If there are too many readings to pack, discard all but the first.
    """
    furigana_readings = [
        format_output(
            word,
            reading
            if cfg.furigana.prefer_literal_pronunciation is False
            else unify_repr(reading)
        )
        for reading in hiragana_readings
    ]
    if 1 < len(furigana_readings):
        return mingle_readings(furigana_readings, sep=cfg.furigana.reading_separator)
    else:
        return furigana_readings[0]


def format_hiragana_readings(readings: list[str]):
    """ Discard kanji and format the readings as hiragana. """
    if 1 < len(readings):
        return f"({cfg.furigana.reading_separator.join(map(to_hiragana, readings))})"
    else:
        return to_hiragana(readings[0])


def discard_extra_readings(readings: Sequence, max_results: int, discard_mode: ReadingsDiscardMode):
    """ Depending on the settings, if there are too many readings, discard some or all but the first. """
    if max_results <= 0 or len(readings) <= max_results:
        return readings
    elif discard_mode == ReadingsDiscardMode.discard_extra:
        return readings[:max_results]
    elif discard_mode == ReadingsDiscardMode.keep_first:
        return readings[:1]
    elif discard_mode == ReadingsDiscardMode.discard_all:
        return []
    else:
        raise ValueError("No handler for mode.")


def format_furigana(out: MecabParsedToken, full_hiragana: bool = False) -> str:
    if is_kana_str(out.word) or cfg.furigana.is_blocklisted(out.word):
        return out.word
    elif readings := list(iter_possible_readings(out)):
        readings = discard_extra_readings(readings, cfg.furigana.maximum_results, cfg.furigana.discard_mode)
        return (
            format_furigana_readings(out.word, readings)
            if full_hiragana is False
            else format_hiragana_readings(readings)
        )
    else:
        return out.word


def try_lookup_full_text(text: str) -> Optional[MecabParsedToken]:
    """
    Try looking up whole text in the accent db.
    Avoids calling mecab when the text contains one word in dictionary form
    or multiple words in dictionary form separated by punctuation.
    """

    if cfg.furigana.can_lookup_in_db(text) and next(iter(iter_accents(text)), None) is not None:
        return MecabParsedToken(
            word=text,
            headword=text,
            katakana_reading=None,
            part_of_speech=None,
            inflection=None
        )


def format_parsed_tokens(tokens: list[Union[MecabParsedToken, Token]], full_hiragana: bool = False) -> Iterable[str]:
    for token in tokens:
        if isinstance(token, MecabParsedToken):
            yield format_furigana(token, full_hiragana)
        elif isinstance(token, str):
            yield token
        else:
            raise ValueError("Invalid type.")


def generate_furigana(src_text: str, split_morphemes: bool = True, full_hiragana: bool = False) -> str:
    substrings = []
    for token in tokenize(src_text, counters=cfg.furigana.counters):
        if not isinstance(token, ParseableToken) or is_kana_str(token):
            # Skip tokens that can't be parsed (non-japanese text).
            # Skip full-kana tokens (no furigana is needed).
            substrings.append(token)
        elif dummy := try_lookup_full_text(token):
            # If full text search succeeded, continue.
            substrings.append(dummy)
        elif split_morphemes is True:
            # Split with mecab, format furigana for each word.
            substrings.extend(mecab_translate(token))
        elif (first := mecab_translate(token)[0]).word == token:
            # If the user doesn't want to split morphemes, still try to find the reading using mecab
            # but abort if mecab outputs more than one word.
            substrings.append(first)
        else:
            substrings.append(token)
    return ''.join(format_parsed_tokens(substrings, full_hiragana)).strip()


# Entry point
##########################################################################


mecab = MecabController(verbose=True)
acc_dict = AccentDictManager()
