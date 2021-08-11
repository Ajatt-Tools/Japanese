# -*- coding: utf-8 -*-

import os
import pickle
import re
from collections import namedtuple
from typing import Dict, List, Tuple

# Paths to the database files and this particular file

addon_dir_path = os.path.dirname(os.path.normpath(__file__))
db_dir_path = os.path.join(addon_dir_path, "accent_dict")
accent_database = os.path.join(db_dir_path, "nhk_data.csv")
derivative_database = os.path.join(db_dir_path, "nhk_pronunciation.csv")
derivative_pickle = os.path.join(db_dir_path, "nhk_pronunciation.pickle")

AccentEntry = namedtuple(
    'AccentEntry',
    [
        'NID', 'ID', 'WAVname', 'K_FLD', 'ACT',
        'katakana_reading', 'nhk', 'kanjiexpr', 'NHKexpr', 'numberchars',
        'devoiced_pos', 'nasalsoundpos', 'majiri', 'kaisi', 'KWAV',
        'katakana_reading_alt', 'akusentosuu', 'bunshou', 'accent',
    ]
)


def make_accent_entry(csv_line: str) -> AccentEntry:
    csv_line = csv_line.strip()
    # Special entries in the CSV file that have to be escaped
    # to prevent them from being treated as multiple fields.
    sub_entries = re.findall(r'({.*?,.*?})', csv_line) + re.findall(r'(\(.*?,.*?\))', csv_line)
    for s in sub_entries:
        csv_line = csv_line.replace(s, s.replace(',', ';'))

    return AccentEntry(*csv_line.split(','))


def format_nasal_or_devoiced_positions(expr: str):
    # Sometimes the expr ends with 10
    if expr.endswith('10'):
        expr = expr[:-2]
        result = [10]
    else:
        result = []

    return result + [int(pos) for pos in expr.split('0') if pos]


def format_entry(e: AccentEntry) -> str:
    """ Format an entry from the data in the original database to something that uses html """
    kana_reading, acc_pattern = e.katakana_reading_alt, e.accent

    # Fix accent notation by prepending zeros for moraes where accent info is omitted in the CSV.
    acc_pattern = "0" * (len(kana_reading) - len(acc_pattern)) + acc_pattern

    # Get the nasal positions
    nasal = format_nasal_or_devoiced_positions(e.nasalsoundpos)

    # Get the devoiced positions
    devoiced = format_nasal_or_devoiced_positions(e.devoiced_pos)

    result_str = []
    overline_flag = False

    for idx, acc in enumerate(int(pos) for pos in acc_pattern):
        # Start or end overline when necessary
        if not overline_flag and acc > 0:
            result_str += '<span class="overline">'
            overline_flag = True
        if overline_flag and acc == 0:
            result_str += '</span>'
            overline_flag = False

        # Wrap character if it's devoiced, else add as is.
        if (idx + 1) in devoiced:
            result_str += f'<span class="nopron">{kana_reading[idx]}</span>'
        else:
            result_str += kana_reading[idx]

        if (idx + 1) in nasal:
            result_str += '<span class="nasal">&#176;</span>'

        # If we go down in pitch, add the downfall
        if acc == 2:
            result_str += '</span>&#42780;'
            overline_flag = False

    # Close the overline if it's still open
    if overline_flag:
        result_str += "</span>"

    return ''.join(result_str)


def build_derivative(dest_path: str = derivative_database) -> None:
    """ Build the derived database from the original database and save it as *.csv """
    temp_dict = {}

    with open(accent_database, 'r', encoding="utf-8") as f:
        entries: List[AccentEntry] = [make_accent_entry(line) for line in f]

    for entry in entries:
        # A tuple holding both the spelling in katakana, and the katakana with pitch/accent markup
        value = (entry.katakana_reading, format_entry(entry))

        # Add expressions for both
        for key in (entry.nhk, entry.kanjiexpr):
            temp_dict[key] = temp_dict.get(key, [])
            if value not in temp_dict[key]:
                temp_dict[key].append(value)

    with open(dest_path, 'w', encoding="utf-8") as of:
        for word in temp_dict.keys():
            for katakana, pitch_html in temp_dict[word]:
                of.write(f"{word}\t{katakana}\t{pitch_html}\n")


def read_derivative() -> Dict[str, List[Tuple[str, str]]]:
    """ Read the derivative file to memory """
    acc_dict = {}
    with open(derivative_database, 'r', encoding="utf-8") as f:
        for line in f:
            word, kana, pitch_html = line.strip().split('\t')
            for key in (word, kana):
                acc_dict[key] = acc_dict.get(key, [])
                if (entry := (kana, pitch_html)) not in acc_dict[key]:
                    acc_dict[key].append(entry)

    return acc_dict


def should_regenerate(file: str) -> bool:
    return any(
        os.path.getmtime(os.path.join(addon_dir_path, f)) > os.path.getmtime(file)
        for f in os.listdir(addon_dir_path) if f.endswith('.py')
    )


def init() -> Dict[str, List[Tuple[str, str]]]:
    if not os.path.isdir(db_dir_path):
        raise IOError("Accent database folder is missing!")

    # First check that either the original database, or the derivative text file are present:
    if not os.path.exists(accent_database) and not os.path.exists(derivative_database):
        raise IOError("Could not locate the original base or the derivative database!")

    for file in (derivative_database, derivative_pickle):
        if os.path.exists(file) and should_regenerate(file):
            print("Will be rebuilt: ", os.path.basename(file))
            os.remove(file)

    # Generate the derivative database if it does not exist yet
    if not os.path.exists(derivative_database):
        build_derivative()

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


def test():
    import filecmp
    test_database = os.path.join(db_dir_path, "test.csv")
    build_derivative(dest_path=test_database)
    print('Equal.' if filecmp.cmp(derivative_database, test_database, shallow=False) else 'Not equal!')


if __name__ == '__main__':
    test()
