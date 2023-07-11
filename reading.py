# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import itertools
from collections import OrderedDict
from typing import Union

from anki.utils import html_to_text_line
from aqt import gui_hooks

from .config_view import config_view as cfg, ReadingsDiscardMode
from .helpers import *
from .helpers.common_kana import adjust_reading
from .helpers.mingle_readings import *
from .helpers.profiles import PitchOutputFormat
from .helpers.tokens import tokenize, split_separators, ParseableToken, clean_furigana, Token
from .mecab_controller.format import format_output
from .mecab_controller.kana_conv import is_kana_str, to_hiragana, to_katakana
from .mecab_controller.mecab_controller import MecabController, MecabParsedToken
from .mecab_controller.unify_readings import literal_pronunciation as pr, unify_repr
from .pitch_accents.acc_dict_mgr import AccentDict, FormattedEntry, AccentDictManager
from .pitch_accents.styles import convert_to_inline_style


# Lookup
##########################################################################


def update_html(html_notation: str) -> str:
    html_notation = convert_to_inline_style(html_notation)
    if cfg.pitch_accent.output_hiragana:
        html_notation = to_hiragana(html_notation)
    return html_notation


@functools.lru_cache(maxsize=cfg.cache_lookups)
def mecab_translate(expr: str) -> tuple[MecabParsedToken, ...]:
    return tuple(mecab.translate(expr))



def should_ignore_incorrect_reading(expr_reading: str) -> bool:
    """
    Don't bother handling readings that contain multiple different words or readings that are numbers.
    Sometimes the reading starts with x or ×, like 明後日[×あさって].
    Used to indicate that one of the two possible readings is not the answer.
    https://tatsumoto-ren.github.io/blog/discussing-various-card-templates.html#distinguishing-readings
    """
    return (
            expr_reading.isnumeric()
            or cfg.furigana.reading_separator.strip() in expr_reading
            or MULTIPLE_READING_SEP in expr_reading
            or expr_reading.startswith('x')
            or expr_reading.startswith('×')
    )


def split_possible_furigana(expr: str) -> WordReading:
    # Sometimes furigana notation is being used by the users to distinguish otherwise duplicate notes.
    # E.g., テスト[1], テスト[2]
    expr = strip_non_jp_furigana(expr)

    # If the expression contains furigana, split it.
    expr, expr_reading = word_reading(expr)
    expr, expr_reading = clean_furigana(expr), clean_furigana(expr_reading)

    # If there are numbers or multiple readings present, ignore all of them.
    if expr_reading and should_ignore_incorrect_reading(expr_reading):
        expr_reading = ''

    return WordReading(expr, expr_reading)


def single_word_reading(word: str):
    """
    Try to look up the reading of a single word using mecab.
    """
    if len(tokens := mecab_translate(word)) == 1 and (token := tokens[-1]).katakana_reading:
        return token.katakana_reading
    return ""


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

    # Handle furigana, if present.
    expr, expr_reading = split_possible_furigana(expr)

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
        expr_reading = (expr_reading or single_word_reading(expr))
        if expr_reading and (lookup_reading := acc_dict.lookup(expr_reading)):
            ret.setdefault(expr, []).extend(lookup_reading)

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
                # Katakana lookups are possible because of the additional key in the pitch accents dictionary.
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


def entries_to_html(entries: Sequence[FormattedEntry], output_format: PitchOutputFormat, max_results: int):
    """
    Convert entries to HTML, sort and remove duplicates.
    """
    entries = sorted(entries, key=lambda entry: (entry.katakana_reading, entry.pitch_number))
    entries = dict.fromkeys(get_notation(entry, output_format) for entry in entries)
    entries = discard_extra_readings(
        list(entries),
        max_results=max_results or cfg.pitch_accent.maximum_results,
        discard_mode=cfg.pitch_accent.discard_mode,
    )
    return entries


def format_pronunciations(
        pronunciations: AccentDict,
        output_format: PitchOutputFormat = PitchOutputFormat.html,
        sep_single: str = "・",
        sep_multi: str = "、",
        expr_sep: str = None,
        max_results: int = None,
) -> str:
    ordered_dict = OrderedDict()
    for word, entries in pronunciations.items():
        if entries := entries_to_html(entries, output_format, max_results=max_results):
            ordered_dict[word] = sep_single.join(entries)

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join(f"{word}{expr_sep}{entries}" for word, entries in ordered_dict.items() if word and entries)
    else:
        txt = sep_multi.join(ordered_dict.values())

    return txt


class AccDbParsedToken(NamedTuple):
    """
    A tuple used to store gathered readings of an expression.
    If readings are found in the accent db, mecab can be bypassed.
    """
    word: str
    hiragana_readings: list[str]


def gather_possible_readings(out: MecabParsedToken) -> AccDbParsedToken:
    """
    Return all possible hiragana readings for the word, e.g. [そそぐ, すすぐ, ゆすぐ].
    If the user doesn't want to look up readings in the pitch accents dictionary,
    return back the one reading contained in the parsed token, which may be empty.
    """
    readings = []

    if out.katakana_reading:
        readings.append(to_hiragana(out.katakana_reading))

    if cfg.furigana.can_lookup_in_db(out.headword):
        for entry in iter_accents(out.headword):
            readings.append(adjust_reading(out.word, out.headword, to_hiragana(entry.katakana_reading)))

    return AccDbParsedToken(out.word, readings)


def format_furigana_readings(word: str, hiragana_readings: list[str]) -> str:
    """
    Pack all readings into this format: "word[reading<sep>reading, ...]suffix".
    If there are too many readings to pack, discard all but the first.
    """
    furigana_readings = [
        format_output(
            word,
            reading=(
                reading
                if cfg.furigana.prefer_literal_pronunciation is False
                else unify_repr(reading)
            ),
        )
        for reading in hiragana_readings
        if reading
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


def discard_extra_readings(readings: list[str], max_results: int, discard_mode: ReadingsDiscardMode) -> list[str]:
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
        raise ValueError(f"No handler for mode {discard_mode}.")


def try_lookup_full_text(text: str) -> Iterable[AccDbParsedToken]:
    """
    Try looking up whole text in the accent db.
    Avoids calling mecab when the text contains one word in dictionary form
    or multiple words in dictionary form separated by punctuation.
    """

    if cfg.furigana.can_lookup_in_db(text) and (results := get_pronunciations(text, recurse=False)):
        for word, entries in results.items():
            yield AccDbParsedToken(
                word=word,
                hiragana_readings=[to_hiragana(entry.katakana_reading) for entry in entries],
            )


def unique_readings(readings: list[str]) -> list[str]:
    """
    Return a list of readings without repetitions.
    """

    def sorted_readings() -> list[str]:
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


def format_acc_db_result(out: AccDbParsedToken, full_hiragana: bool = False) -> str:
    """
    Given a word and a list of its readings, produce the appropriate furigana or kana output.
    """
    if is_kana_str(out.word) or cfg.furigana.is_blocklisted(out.word):
        return out.word

    readings = discard_extra_readings(
        unique_readings(out.hiragana_readings),
        max_results=cfg.furigana.maximum_results,
        discard_mode=cfg.furigana.discard_mode,
    )

    if not readings:
        return out.word

    if full_hiragana:
        return format_hiragana_readings(readings)

    return format_furigana_readings(out.word, readings)


def format_parsed_tokens(
        tokens: list[Union[AccDbParsedToken, MecabParsedToken, Token]],
        full_hiragana: bool = False
) -> Iterable[str]:
    for token in tokens:
        if isinstance(token, AccDbParsedToken):
            yield format_acc_db_result(token, full_hiragana=full_hiragana)
        elif isinstance(token, MecabParsedToken):
            yield format_acc_db_result(gather_possible_readings(token), full_hiragana=full_hiragana)
        elif isinstance(token, str):
            yield token
        else:
            raise ValueError(f"Invalid type: {type(token)}")


def generate_furigana(src_text: str, split_morphemes: bool = True, full_hiragana: bool = False) -> str:
    substrings = []
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
gui_hooks.main_window_did_init.append(acc_dict.reload_from_disk)
