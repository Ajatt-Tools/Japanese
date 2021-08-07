# -*- coding: utf-8 -*-

import pickle
from collections import namedtuple
from typing import Tuple

from aqt.qt import *

from .helpers import *

# Paths to the database files and this particular file

this_addon_path = os.path.dirname(os.path.normpath(__file__))
db_dir_path = os.path.join(this_addon_path, "accent_dict")
accent_database = os.path.join(db_dir_path, "ACCDB_unicode.csv")
derivative_database = os.path.join(db_dir_path, "nhk_pronunciation.csv")
derivative_pickle = os.path.join(db_dir_path, "nhk_pronunciation.pickle")

AccentEntry = namedtuple(
    'AccentEntry',
    [
        'NID', 'ID', 'WAVname', 'K_FLD', 'ACT', 'kana_reading', 'nhk', 'kanjiexpr', 'NHKexpr',
        'numberchars', 'nopronouncepos', 'nasalsoundpos', 'majiri', 'kaisi', 'KWAV', 'kana_reading_alt',
        'akusentosuu', 'bunshou', 'accent'
    ]
)


def format_entry(e: AccentEntry) -> str:
    """ Format an entry from the data in the original database to something that uses html """
    kana = e.kana_reading_alt
    acc_pattern = "0" * (len(kana) - len(e.accent)) + e.accent

    # Get the nasal positions
    nasal = []
    if e.nasalsoundpos:
        positions = e.nasalsoundpos.split('0')
        for p in positions:
            if p:
                nasal.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nasal[-1] = nasal[-1] * 10

    # Get the no pronounce positions
    nopron = []
    if e.nopronouncepos:
        positions = e.nopronouncepos.split('0')
        for p in positions:
            if p:
                nopron.append(int(p))
            if not p:
                # e.g. "20" would result in ['2', '']
                nopron[-1] = nopron[-1] * 10

    result_str = ""
    overline_flag = False

    for i in range(len(kana)):
        a = int(acc_pattern[i])
        # Start or end overline when necessary
        if not overline_flag and a > 0:
            result_str = result_str + '<span class="overline">'
            overline_flag = True
        if overline_flag and a == 0:
            result_str = result_str + '</span>'
            overline_flag = False

        if (i + 1) in nopron:
            result_str = result_str + '<span class="nopron">'

        # Add the character stuff
        result_str = result_str + kana[i]

        # Add the pronunciation stuff
        if (i + 1) in nopron:
            result_str = result_str + "</span>"
        if (i + 1) in nasal:
            result_str = result_str + '<span class="nasal">&#176;</span>'

        # If we go down in pitch, add the downfall
        if a == 2:
            result_str = result_str + '</span>&#42780;'
            overline_flag = False

    # Close the overline if it's still open
    if overline_flag:
        result_str = result_str + "</span>"

    return result_str


def build_database() -> None:
    """ Build the derived database from the original database """
    temp_dict = {}
    entries = []

    with open(accent_database, 'r', encoding="utf-8") as file_handle:
        for line in file_handle:
            line = line.strip()
            substrs = re.findall(r'({.*?,.*?})', line)
            substrs.extend(re.findall(r'(\(.*?,.*?\))', line))
            for s in substrs:
                line = line.replace(s, s.replace(',', ';'))
            entries.append(AccentEntry(*line.split(',')))

    for e in entries:
        # A tuple holding both the spelling in katakana, and the katakana with pitch/accent markup
        kana_pron = (e.kana_reading, format_entry(e))

        # Add expressions for both
        for key in [e.nhk, e.kanjiexpr]:
            if key in temp_dict:
                if kana_pron not in temp_dict[key]:
                    temp_dict[key].append(kana_pron)
            else:
                temp_dict[key] = [kana_pron]

    with open(derivative_database, 'w', encoding="utf-8") as o:
        for key in temp_dict.keys():
            for kana, pron in temp_dict[key]:
                o.write("%s\t%s\t%s\n" % (key, kana, pron))


def read_derivative() -> Dict[str, List[Tuple[str, str]]]:
    """ Read the derivative file to memory """
    acc_dict = {}
    with open(derivative_database, 'r', encoding="utf-8") as f:
        for line in f:
            key, kana, pron = line.strip().split('\t')
            entry = (kana, pron)
            if key in acc_dict:
                if entry not in acc_dict[key]:
                    acc_dict[key].append(entry)
            else:
                acc_dict[key] = [entry, ]

    return acc_dict


def init() -> Dict[str, List[Tuple[str, str]]]:
    if not os.path.isdir(db_dir_path):
        raise IOError("Accent database folder is missing!")

    # First check that either the original database, or the derivative text file are present:
    if not os.path.exists(accent_database) and not os.path.exists(derivative_database):
        raise IOError("Could not locate the original base or the derivative database!")

    # Generate the derivative database if it does not exist yet
    if not os.path.exists(derivative_database):
        build_database()

    # If a pickle exists of the derivative file, use that.
    # Otherwise, read from the derivative file and generate a pickle.
    if os.path.exists(derivative_pickle):
        with open(derivative_pickle, 'rb') as f:
            return pickle.load(f)
    else:
        with open(derivative_pickle, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(derivative := read_derivative(), f, pickle.HIGHEST_PROTOCOL)
        return derivative
