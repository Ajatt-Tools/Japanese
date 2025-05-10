# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from ..mecab_controller.kana_conv import is_kana_str
from ..mecab_controller.kana_conv import to_katakana as _


def adjust_to_inflection(raw_word: str, headword: str, headword_reading: str) -> str:
    """
    Adjusts the word's reading to match its conjugated form.
    E.g., if raw_word is 食べた and the reading is たべる, it should output たべた.
    """
    if _(headword) == _(headword_reading):
        # or maybe return headword_reading
        return raw_word
    if _(headword) == _(raw_word):
        return headword_reading
    if is_kana_str(raw_word):
        return raw_word

    # Analyze the headword.
    # Go from the last to the first character
    # and skip the characters that are identical between the headword and the reading.
    # In the end, the reading of a common `stem` should be found, e.g. "ひざまず" for "跪かなかった"
    idx_headword, idx_reading = len(headword), len(headword_reading)
    while _(headword[idx_headword - 1]) == _(headword_reading[idx_reading - 1]):
        idx_headword -= 1
        idx_reading -= 1
    stem_reading = headword_reading[:idx_reading]
    inflected_reading = raw_word[idx_headword:]

    if _(stem_reading) == _(headword_reading):
        return headword_reading
    return stem_reading + inflected_reading
