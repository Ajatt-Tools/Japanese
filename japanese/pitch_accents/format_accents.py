# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence
from typing import Union

from ..mecab_controller.unify_readings import literal_pronunciation
from .styles import XmlTags


def format_one_mora_word(moras: Sequence[str], is_flat: bool) -> str:
    assert len(moras) == 1
    if is_flat:
        # _/
        return "".join((
            XmlTags.low_rise_start,
            *moras,
            XmlTags.low_rise_end,
        ))
    else:
        # ‾\
        return "".join((
            XmlTags.high_drop_start,
            *moras,
            XmlTags.high_drop_end,
        ))


def format_atamadaka(moras: Sequence[str]) -> str:
    # ‾\___
    return "".join((
        # ‾\
        XmlTags.high_drop_start,
        moras[0],
        XmlTags.high_drop_end,
        # ___
        XmlTags.low_start,
        *moras[1:],
        XmlTags.low_end,
    ))


def format_heiban(moras: Sequence[str]) -> str:
    # _/‾‾‾
    return "".join((
        # _/
        XmlTags.low_rise_start,
        moras[0],
        XmlTags.low_rise_end,
        # ‾‾‾
        XmlTags.high_start,
        *moras[1:],
        XmlTags.high_end,
    ))


def format_odaka(moras: Sequence[str]):
    # _/‾‾‾\
    return "".join((
        # _/
        XmlTags.low_rise_start,
        moras[0],
        XmlTags.low_rise_end,
        # ‾‾‾\
        XmlTags.high_drop_start,
        *moras[1:],
        XmlTags.high_drop_end,
    ))


def format_nakadaka(moras: Sequence[str], accent: int) -> str:
    low_before, high, low_after = moras[:1], moras[1:accent], moras[accent:]

    # _/‾‾‾\___
    return "".join((
        # _/
        XmlTags.low_rise_start,
        *low_before,
        XmlTags.low_rise_end,
        # ‾‾‾\
        XmlTags.high_drop_start,
        *high,
        XmlTags.high_drop_end,
        # ___
        XmlTags.low_start,
        *low_after,
        XmlTags.low_end,
    ))


def format_entry(moras: Sequence[str], accent: Union[int, str]) -> str:
    """Format an entry from the data in the original pitch accents file to something that uses html"""

    if type(accent) is not int:
        return literal_pronunciation("".join(moras))
    elif len(moras) == 1:
        return format_one_mora_word(moras, is_flat=(accent == 0))
    elif accent == 0:
        return format_heiban(moras)
    elif accent == 1:
        return format_atamadaka(moras)
    elif accent == len(moras):
        return format_odaka(moras)
    else:
        return format_nakadaka(moras, accent)
