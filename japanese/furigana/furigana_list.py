# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from typing import MutableSequence, Iterable, Union

from ..helpers.tokens import Token
from ..mecab_controller import is_kana_str
from ..mecab_controller.basic_types import Inflection, ANY_ATTACHING, PartOfSpeech
from ..pitch_accents.basic_types import AccDbParsedToken

AnyToken = Union[AccDbParsedToken, Token]


def is_attaching(self: Inflection) -> bool:
    if self == self.unknown:
        return False
    return (
            ANY_ATTACHING in self.value
            or self == self.hypothetical
            or self == self.irrealis
            or self == self.irrealis_nu
            or self == self.irrealis_reru
            or self == self.irrealis_special
            or self == self.continuative
    )


def is_kana_token(token: AnyToken) -> bool:
    try:
        return is_kana_str(token.word)
    except AttributeError:
        return is_kana_str(str(token))


def token_as_kana_word(token: AnyToken) -> str:
    try:
        return token.word
    except AttributeError:
        return str(token)


def should_attach_token(attach_to: AccDbParsedToken, token: AccDbParsedToken):
    if not is_attaching(attach_to.inflection_type):
        return False
    if not is_kana_token(token):
        return False
    if token.part_of_speech == PartOfSpeech.noun:
        return False
    return True


class FuriganaList:
    _list: MutableSequence[AnyToken]

    def __init__(self) -> None:
        self._list = []

    def append(self, token: AnyToken) -> None:
        try:
            if should_attach_token(self.back(), token):
                self.back().attached_tokens.append(token_as_kana_word(token))
                return
        except (IndexError, AttributeError):
            pass
        self._list.append(token)

    def extend(self, tokens: Iterable[AnyToken]) -> None:
        for token in tokens:
            self.append(token)

    def back(self) -> AnyToken:
        if not self._list:
            raise IndexError("List is empty.")
        return self._list[-1]

    def __iter__(self):
        return iter(self._list)
