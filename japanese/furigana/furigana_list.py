# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable, MutableSequence
from typing import Union

from ..helpers.inflections import longest_kana_suffix
from ..helpers.tokens import Token
from ..mecab_controller.basic_types import ANY_ATTACHING, Inflection
from ..mecab_controller.kana_conv import is_hiragana_str
from ..pitch_accents.basic_types import AccDbParsedToken
from .attach_rules import (
    DETACH_HEADWORDS,
    DETACH_PAIRS,
    DETACH_POS,
    DETACH_WORDS,
    MAX_ATTACHED,
    TAPE_PAIRS,
)

AnyToken = Union[AccDbParsedToken, Token]


class TokenAccessError(Exception):
    pass


def is_attaching_inflection(inflection: Inflection) -> bool:
    if inflection == inflection.unknown:
        return False
    return (
        ANY_ATTACHING in inflection.value
        or inflection == inflection.hypothetical
        or inflection == inflection.irrealis
        or inflection == inflection.irrealis_nu
        or inflection == inflection.irrealis_reru
        or inflection == inflection.irrealis_special
        or inflection == inflection.continuative
    )


def prev_token(attach_to: AccDbParsedToken) -> str:
    return attach_to.attached_tokens[-1] if attach_to.attached_tokens else longest_kana_suffix(attach_to.word)


def is_taped_pair(attach_to: AccDbParsedToken, token: AnyToken):
    return (prev_token(attach_to), token.word) in TAPE_PAIRS


def is_detached_pair(attach_to: AccDbParsedToken, token: AnyToken):
    return (prev_token(attach_to), token.word) in DETACH_PAIRS


def should_attach_token(attach_to: AccDbParsedToken, token: AnyToken):
    if len(attach_to.attached_tokens) >= MAX_ATTACHED:
        return False
    if not is_attaching_inflection(attach_to.inflection_type):
        return False
    if not is_hiragana_str(token.word):
        # only kana can be attached to the previous word, e.g. 探し(+た)
        return False
    if is_taped_pair(attach_to, token):
        return True
    if is_detached_pair(attach_to, token):
        return False
    if token.part_of_speech in DETACH_POS:
        return False
    if token.word in DETACH_WORDS or token.headword in DETACH_HEADWORDS:
        return False
    return True


class FuriganaList:
    _list: MutableSequence[AnyToken]

    def __init__(self) -> None:
        self._list = []

    def append_token(self, token: AnyToken) -> None:
        try:
            attach_to = self.last_token_if_known_accent()
        except TokenAccessError:
            pass
        else:
            if should_attach_token(attach_to, token):
                attach_to.attached_tokens.append(token.word)
                return
        self._list.append(token)

    def extend(self, tokens: Iterable[AnyToken]) -> None:
        for token in tokens:
            self.append_token(token)

    def last_token_if_known_accent(self) -> AccDbParsedToken:
        last = self.back()
        if not isinstance(last, AccDbParsedToken):
            raise TokenAccessError("Last token is not parsed.")
        # not stictly necessary:
        # if not last.has_pitch():
        #     raise TokenAccessError("Last token has no known pitch accent.")
        return last

    def back(self) -> AnyToken:
        if not self._list:
            raise TokenAccessError("List is empty.")
        return self._list[-1]

    def __iter__(self):
        return iter(self._list)
