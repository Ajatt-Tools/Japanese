# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import collections
import os
import pickle
import typing
from collections.abc import Sequence

from aqt import mw
from aqt.operations import QueryOp

from ..mecab_controller.kana_conv import to_katakana
from .common import (
    AccentDict,
    FormattedEntry,
    OrderedSet,
    repack_accent_dict,
    should_regenerate,
)
from .consts import FORMATTED_ACCENTS_PICKLE, FORMATTED_ACCENTS_TSV, RES_DIR_PATH
from .user_accents import UserAccentData


class AccDictRawTSVEntry(typing.TypedDict):
    """Entry as it appears in the pitch accents file."""

    headword: str
    katakana_reading: str
    html_notation: str
    pitch_number: str  # can't be converted to int. might contain separators and special symbols.
    frequency: str  # must be converted to int. larger number => more occurrences.


def get_tsv_reader(f: typing.Iterable[str]) -> csv.DictReader:
    """
    Prepare a reader to load the accent dictionary.
    Keys are already included in the csv file.
    """
    return csv.DictReader(
        f,
        dialect="excel-tab",
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )


def read_formatted_accents() -> AccentDict:
    """
    Read the formatted pitch accents file to memory.
    Place items in a list to retain the provided order of readings.

    Example entry as it appears in the formatted file:
    新年会 シンネンカイ <low_rise>シ</low_rise><high_drop>ンネ</high_drop><low>ンカイ</low> 3
    """
    acc_dict: dict[str, OrderedSet[FormattedEntry]] = collections.defaultdict(OrderedSet)
    row: AccDictRawTSVEntry
    with open(FORMATTED_ACCENTS_TSV, newline="", encoding="utf-8") as f:
        for row in get_tsv_reader(f):
            entry = FormattedEntry(
                katakana_reading=row["katakana_reading"],
                html_notation=row["html_notation"],
                pitch_number=row["pitch_number"],
            )
            for key in (row["headword"], row["katakana_reading"]):
                acc_dict[to_katakana(key)].add(entry)
    return repack_accent_dict(acc_dict)


def accents_dict_init() -> AccentDict:
    if not os.path.isdir(RES_DIR_PATH):
        raise OSError("Pitch accents folder is missing!")

    acc_dict = AccentDict({})
    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if should_regenerate(FORMATTED_ACCENTS_PICKLE):
        assert not acc_dict
        print("The pickle needs updating.")
        acc_dict.update(read_formatted_accents())
        with open(FORMATTED_ACCENTS_PICKLE, "wb") as f:
            # Pickle the dictionary using the highest protocol available.
            pickle.dump(acc_dict, f, pickle.HIGHEST_PROTOCOL)
    else:
        assert not acc_dict
        print("Reading from existing accents pickle.")
        try:
            with open(FORMATTED_ACCENTS_PICKLE, "rb") as f:
                acc_dict.update(pickle.load(f))
        except ModuleNotFoundError:
            # tried to load the pickle file and failed
            os.unlink(FORMATTED_ACCENTS_PICKLE)
            return accents_dict_init()

    # Finally, patch with user-defined entries.
    acc_dict.update(UserAccentData().create_formatted())
    return acc_dict


class AccentDictManager:
    def __init__(self) -> None:
        self._db: AccentDict = AccentDict({})

    def __contains__(self, item: str) -> bool:
        return self._db.__contains__(item)

    def __getitem__(self, item: str) -> Sequence[FormattedEntry]:
        return self._db.__getitem__(item)

    def lookup(self, expr: str) -> typing.Optional[Sequence[FormattedEntry]]:
        """
        Look up expr in accent db, always as katakana.
        Return None if there's no pitch accent for expr.
        """
        try:
            return self[to_katakana(expr)]
        except KeyError:
            return None

    def reload_from_disk(self) -> None:
        """Reads pitch accents file from disk."""

        print("Reading pitch accents file...")
        assert mw
        QueryOp(
            parent=mw,
            op=lambda collection: accents_dict_init(),
            success=lambda dictionary: self._reload_dict(dictionary),
        ).without_collection().with_progress(
            "Reloading pitch accent dictionary...",
        ).run_in_background()

    def _reload_dict(self, new_dict: AccentDict) -> None:
        """Reloads accent db (e.g. when the user changed settings)."""
        print("Reloading accent dictionary...")
        self._db.clear()
        self._db.update(new_dict)
        print(f"Total pitch accent entries: {len(self._db)}.")

    def reload_on_main(self) -> None:
        """Used in tests"""
        assert mw is None
        self._reload_dict(accents_dict_init())
