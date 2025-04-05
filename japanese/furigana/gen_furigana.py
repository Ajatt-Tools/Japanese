# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
from collections.abc import Hashable, Iterable, Sequence
from typing import Callable, Optional, TypeVar

from ..config_view import FuriganaConfigView, JapaneseConfig
from ..database.sqlite3_buddy import Sqlite3Buddy
from ..helpers.common_kana import adjust_to_inflection
from ..helpers.consts import LONG_VOWEL_MARK
from ..helpers.mingle_readings import mingle_readings
from ..helpers.profiles import ColorCodePitchFormat
from ..helpers.tokens import ParseableToken, Token, tokenize
from ..mecab_controller import MecabController, format_output, is_kana_str, to_hiragana
from ..mecab_controller.basic_types import Inflection, MecabParsedToken, PartOfSpeech
from ..mecab_controller.unify_readings import literal_pronunciation as pr
from ..mecab_controller.unify_readings import unify_repr
from ..pitch_accents.accent_lookup import AccentLookup
from ..pitch_accents.basic_types import AccDbParsedToken, PitchAccentEntry
from ..pitch_accents.common import FormattedEntry
from .color_code_wrapper import ColorCodeWrapper
from .furigana_list import FuriganaList

T = TypeVar("T")


def as_self(val):
    return val


class FuriganaGen:
    _cfg: JapaneseConfig
    _fcfg: FuriganaConfigView
    _mecab: MecabController
    _lookup: AccentLookup

    def __init__(self, cfg: JapaneseConfig, lookup: AccentLookup, mecab: Optional[MecabController] = None) -> None:
        self._cfg = cfg
        self._fcfg = cfg.furigana
        self._lookup = lookup
        self._mecab = mecab or self._lookup.mecab

    def with_new_buddy(self, db: Sqlite3Buddy):
        return type(self)(
            cfg=self._cfg,
            mecab=self._mecab,
            lookup=self._lookup.with_new_buddy(db),
        )

    def generate_furigana(
        self,
        src_text: str,
        *,
        split_morphemes: bool = True,
        full_hiragana: bool = False,
        output_format: ColorCodePitchFormat = ColorCodePitchFormat(0),
    ) -> str:
        substrings = FuriganaList()
        for token in tokenize(src_text):
            assert token, "token can't be empty"
            if not isinstance(token, ParseableToken):
                assert isinstance(token, Token), "tokenize() must only yield tokens."
                # Skip tokens that can't be parsed (non-japanese text).
                # Skip full-kana tokens (no furigana is needed).
                substrings.append_token(token)
            elif acc_db_result := tuple(self.try_lookup_full_text(token)):
                # If full text search succeeded, continue.
                substrings.extend(acc_db_result)
            elif split_morphemes is True:
                # Split with mecab, format furigana for each word.
                substrings.extend(self.append_accents(out) for out in self._mecab.translate(token))
            elif out := self.mecab_single_word(token):
                # If the user doesn't want to split morphemes, still try to find the reading using mecab
                # but abort if mecab outputs more than one word.
                substrings.append_token(self.append_accents(out))
            else:
                # Add the string as is, without furigana.
                substrings.append_token(token)
        return "".join(
            self.format_parsed_tokens(
                tokens=substrings,
                full_hiragana=full_hiragana,
                output_format=output_format,
            )
        ).strip()

    def mecab_single_word(self, token: Token) -> Optional[MecabParsedToken]:
        if (out := self._mecab.translate(token)) and out[0].word == token:
            return out[0]
        return None

    def format_furigana_readings(self, word: str, hiragana_readings: Sequence[str]) -> str:
        """
        Pack all readings into this format: "word[reading<sep>reading, ...]suffix".
        If there are too many readings to pack, discard all but the first.
        """
        furigana_readings = [
            format_output(
                word,
                reading=(unify_repr(reading) if self._fcfg.prefer_literal_pronunciation else reading),
            )
            for reading in hiragana_readings
            if reading
        ]
        if len(furigana_readings) > 1:
            return mingle_readings(furigana_readings, sep=self._fcfg.reading_separator)
        else:
            return furigana_readings[0]

    def format_hiragana_readings(self, readings: Sequence[str]) -> str:
        """Discard kanji and format the readings as hiragana."""
        if len(readings) > 1:
            return f"({self._fcfg.reading_separator.join(map(to_hiragana, readings))})"
        else:
            return to_hiragana(readings[0])

    def all_hiragana_readings(self, token: AccDbParsedToken) -> Iterable[str]:
        """
        Yield all possible hiragana readings for the word, e.g. [そそぐ, すすぐ, ゆすぐ].
        """
        if token.katakana_reading:
            yield to_hiragana(token.katakana_reading)
        if not self._fcfg.can_lookup_in_db(token.headword):
            # if the user doesn't want any more readings,
            # e.g. the word is added to "mecab_only" or "maximum_results" is set to 1,
            # then exit early.
            return
        for entry in token.headword_accents:
            yield adjust_to_inflection(
                raw_word=token.word,
                headword=token.headword,
                headword_reading=to_hiragana(entry.katakana_reading),
            )

    def format_parsed_tokens(
        self,
        tokens: FuriganaList,
        full_hiragana: bool,
        output_format: ColorCodePitchFormat,
    ) -> Iterable[str]:
        for token in tokens:
            if isinstance(token, AccDbParsedToken):
                yield self.color_code_pitch(
                    token=token,
                    furigana_formatted=self.format_acc_db_result(token, full_hiragana=full_hiragana),
                    output_format=output_format,
                )
            elif isinstance(token, str):
                yield token
            else:
                raise ValueError(f"Invalid type: {type(token)}")

    def color_code_pitch(
        self, token: AccDbParsedToken, furigana_formatted: str, output_format: ColorCodePitchFormat
    ) -> str:
        with ColorCodeWrapper(token, output_format, self._cfg) as output:
            output.write(furigana_formatted)
            for attached in token.attached_tokens:
                output.write(attached)
            return output.getvalue()

    def format_acc_db_result(self, out: AccDbParsedToken, full_hiragana: bool = False) -> str:
        """
        Given a word and a list of its readings, produce the appropriate furigana or kana output.
        """
        if is_kana_str(out.word) or self._fcfg.is_blocklisted(out.word):
            return out.word

        readings = self.unique_readings(self.all_hiragana_readings(out))
        readings = readings[: self._fcfg.maximum_results]

        if not readings:
            return out.word

        if full_hiragana:
            return self.format_hiragana_readings(readings)

        return self.format_furigana_readings(out.word, readings)

    def try_lookup_full_text(self, text: str) -> Iterable[AccDbParsedToken]:
        """
        Try looking up whole text in the accent db.
        Avoids calling mecab when the text contains one word in dictionary form
        or multiple words in dictionary form separated by punctuation.
        """
        word: str
        entries: Sequence[FormattedEntry]

        if not self._fcfg.can_lookup_in_db(text):
            # pitch accents will be added after parsing with mecab.
            return

        if results := self._lookup.get_pronunciations(text, recurse=False):
            for word, entries in results.items():
                yield AccDbParsedToken(
                    headword=word,
                    word=word,
                    part_of_speech=PartOfSpeech.unknown,
                    inflection_type=Inflection.dictionary_form,
                    katakana_reading=None,
                    headword_accents=self.unique_headword_accents(entries),
                )

    def append_accents(self, token: MecabParsedToken) -> AccDbParsedToken:
        """
        Append readings from the accent dictionary to the reading given by mecab.
        """
        return AccDbParsedToken(
            **dataclasses.asdict(token),
            headword_accents=self.unique_headword_accents(self.iter_accents(token.headword)),
        )

    def _is_reading_preferable(self, reading: str) -> bool:
        return (LONG_VOWEL_MARK in reading) is self._fcfg.prefer_literal_pronunciation

    def _to_unique_readings(
        self,
        entries: Iterable[T],
        *,
        access_key: Callable[[T], Hashable] = as_self,
        access_reading: Callable[[T], str] = as_self,
    ) -> Iterable[T]:
        """
        Return a list of readings without repetitions.
        """
        key_to_entry = {}
        for entry in entries:
            if (access_key(entry) not in key_to_entry) or self._is_reading_preferable(access_reading(entry)):
                key_to_entry[access_key(entry)] = entry
        return key_to_entry.values()

    def unique_headword_accents(self, entries: Iterable[FormattedEntry]) -> Sequence[PitchAccentEntry]:
        """
        Returns a list of pitch accents without duplicates.
        """
        return [
            PitchAccentEntry.from_formatted(entry)
            for entry in self._to_unique_readings(
                entries,
                access_key=lambda entry: (pr(entry.katakana_reading), entry.pitch_number),
                access_reading=lambda entry: entry.katakana_reading,
            )
        ]

    def unique_readings(self, readings: Iterable[str]) -> Sequence[str]:
        """
        Return a list of readings without repetitions.
        """
        return [*self._to_unique_readings(readings, access_key=lambda reading: pr(reading))]

    def iter_accents(self, word: str) -> Iterable[FormattedEntry]:
        if word in (accents := self._lookup.get_pronunciations(word, recurse=False)):
            yield from accents[word]
