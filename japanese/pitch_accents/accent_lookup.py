# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections import OrderedDict
from typing import Optional

from aqt import mw

from ..config_view import JapaneseConfig
from ..helpers.mingle_readings import split_possible_furigana
from ..helpers.sqlite3_buddy import Sqlite3Buddy
from ..helpers.tokens import split_separators
from ..mecab_controller import MecabController
from ..mecab_controller.unify_readings import literal_pronunciation as pr
from .acc_dict_mgr_2 import SqliteAccDictReader
from .common import AccentDict


def html_to_text_line(text: str) -> str:
    from anki.utils import html_to_text_line as fn

    try:
        return fn(text)
    except AttributeError:
        assert mw is None
        return text


class AccentLookup:
    _cfg: JapaneseConfig
    _mecab: MecabController
    _db: Optional[Sqlite3Buddy]
    _cache: dict[tuple[str, bool, bool, bool], AccentDict] = {}

    def __init__(self, cfg: JapaneseConfig, mecab: MecabController, db: Optional[Sqlite3Buddy] = None) -> None:
        self._db = db
        self._cfg = cfg
        self._mecab = mecab

    @property
    def db(self) -> Sqlite3Buddy:
        if self._db:
            return self._db
        raise ValueError("db is None")

    def with_new_buddy(self, db: Sqlite3Buddy):
        return type(self)(
            cfg=self._cfg,
            mecab=self._mecab,
            db=db,
        )

    def get_pronunciations(
        self, expr: str, *, sanitize: bool = True, recurse: bool = True, use_mecab: bool = True
    ) -> AccentDict:
        key = (expr, sanitize, recurse, use_mecab)
        try:
            return self._cache[key]
        except KeyError:
            return self._cache.setdefault(
                key,
                self._get_pronunciations(expr, sanitize=sanitize, recurse=recurse, use_mecab=use_mecab),
            )

    def _get_pronunciations(
        self, expr: str, *, sanitize: bool = True, recurse: bool = True, use_mecab: bool = True
    ) -> AccentDict:
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
        expr, expr_reading = split_possible_furigana(expr, self._cfg.furigana.reading_separator)

        # Skip empty strings and user-specified blocklisted words
        if not expr or self._cfg.pitch_accent.is_blocklisted(expr):
            return ret

        reader = SqliteAccDictReader(self.db)

        # Look up the main expression.
        if lookup_main := reader.look_up(expr):
            ret.setdefault(expr, []).extend(
                entry
                for entry in lookup_main
                # if there's furigana, and it doesn't match the entry, skip.
                if not expr_reading or pr(entry.katakana_reading) == pr(expr_reading)
            )

        # If there's furigana, e.g. when using the VocabFurigana field as the source,
        # or if the kana reading of the full expression can be sourced from mecab,
        # and the user wants to perform kana lookups, then try the reading.
        if not ret and self._cfg.pitch_accent.kana_lookups:
            expr_reading = expr_reading or self.single_word_reading(expr)
            if expr_reading and (lookup_reading := reader.look_up(expr_reading)):
                ret.setdefault(expr, []).extend(lookup_reading)

        # Try to split the expression in various ways (punctuation, whitespace, etc.),
        # and check if any of those brings results.
        if not ret and recurse:
            for section in split_separators(expr):
                ret.update(self._get_pronunciations_part(section, use_mecab=use_mecab))
        return ret

    def _get_pronunciations_part(self, expr_part: str, *, use_mecab: bool) -> AccentDict:
        """
        Search pitch accent info (pronunciations) for a part of expression.
        The part must be already sanitized.
        (If enabled and) if the part is not present in the accent dictionary, Mecab is used to split it further.
        """
        ret: AccentDict
        ret = AccentDict(OrderedDict())
        # Sanitize is always set to False because the part must be already sanitized.
        ret.update(self._get_pronunciations(expr_part, sanitize=False, recurse=False))

        # Only if lookups were not successful, we try splitting with Mecab
        if not ret and use_mecab is True:
            for out in self._mecab.translate(expr_part):
                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-expression.
                ret.update(self._get_pronunciations(out.headword, sanitize=False, recurse=False))

                # If everything failed, try katakana lookups.
                # Katakana lookups are possible because of the additional key in the pitch accents dictionary.
                # If the word was in conjugated form, this lookup will also fail.
                if out.headword not in ret and out.katakana_reading and self._cfg.pitch_accent.kana_lookups is True:
                    ret.update(self._get_pronunciations(out.katakana_reading, sanitize=False, recurse=False))
        return ret

    def single_word_reading(self, word: str) -> str:
        """
        Try to look up the reading of a single word using mecab.
        """
        if len(tokens := self._mecab.translate(word)) == 1 and tokens[-1].katakana_reading:
            return tokens[-1].katakana_reading
        return ""
