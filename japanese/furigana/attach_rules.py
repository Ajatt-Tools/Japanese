# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from ..mecab_controller.basic_types import PartOfSpeech

SKIP_COLORING = frozenset(
    (
        PartOfSpeech.other,
        PartOfSpeech.filler,
        PartOfSpeech.particle,
        PartOfSpeech.symbol,
    )
)
NEVER_ATTACH_POS = frozenset(
    (
        PartOfSpeech.adverb,
        PartOfSpeech.noun,
        PartOfSpeech.adnominal_adjective,
        PartOfSpeech.interjection,
    )
)
NEVER_ATTACH_WORD = frozenset(
    (
        "です",
        "いれ",
        "ば",
        "おく",
        "させる",
        "ごめん",
        "もらう",
        "いく",
        "くださる",
        "くる",
        "から",
        "かねる",
        "あの",
        "すぐ",
        "ね",
        "か",
        "なぁ",
        "なあ",
        "とか",
        "けど",
        "だけ",
        "だろ",
        "でしょ",
        "なる",
        "は",
        "が",
        "の",
        "しまう",
        "おる",
        "ある",
        "な",
        "ん",
        "じゃ",
        "らしい",
        "し",
        "も",
        "ほど",
        "いける",
        "たらしい",
    )
)
NEVER_ATTACH_HEADWORD = frozenset(
    (
        "いれ",
        "ば",
        "おく",
        "させる",
        "ごめん",
        "もらう",
        "いく",
        "くださる",
        "くる",
        "から",
        "かねる",
        "あの",
        "すぐ",
        "ね",
        "か",
        "なぁ",
        "なあ",
        "とか",
        "けど",
        "だけ",
        "だろ",
        "でしょ",
        "なる",
        "は",
        "が",
        "の",
        "しまう",
        "おる",
        "ある",
        "な",
        "ん",
        "じゃ",
        "らしい",
        "し",
        "も",
        "ほど",
        "いける",
        "たらしい",
    )
)
MAX_ATTACHED = 4
