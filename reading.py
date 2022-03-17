# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import re
from collections import OrderedDict
from typing import Tuple, NamedTuple, Optional, Iterable

from anki.notes import Note
from anki.utils import htmlToTextLine
from aqt import mw

from .config_view import config_view as cfg
from .database import AccentDict, FormattedEntry
from .database import init as database_init
from .helpers import *
from .helpers.common_kana import adjust_reading
from .helpers.config import Task, TaskMode, iter_tasks
from .helpers.hooks import collection_will_add_note
from .helpers.mingle_readings import mingle_readings, word_reading
from .helpers.tokens import tokenize, split_separators, ParseableToken
from .helpers.unify_readings import unify_repr
from .mecab_controller import BasicMecabController
from .mecab_controller import format_output, is_kana_word
from .mecab_controller import to_hiragana, to_katakana


# Mecab controller
##########################################################################

class ParsedToken(NamedTuple):
    word: str
    katakana_reading: Optional[str]
    headword: str

    @property
    def hiragana_reading(self) -> str:
        return to_hiragana(self.katakana_reading)


class MecabController(BasicMecabController):
    _add_mecab_args = [
        '--node-format=%m,%f[7],%f[6]\t',
        '--unk-format=%m\t',
        '--eos-format=\n',
    ]

    def __init__(self):
        super().__init__(mecab_args=self._add_mecab_args)

    @staticmethod
    def escape_text(text: str) -> str:
        """Strip characters that trip up mecab."""
        text = text.replace("\n", " ")
        text = text.replace('\uff5e', "~")
        text = re.sub("<br( /)?>", "---newline---", text)
        text = htmlToTextLine(text)
        text = text.replace("---newline---", "<br>")
        return text

    def translate(self, expr: str) -> Iterable[ParsedToken]:
        """ Returns dictionary form and reading for each word in expr. """
        expr = self.escape_text(expr)

        for section in self.run(expr).split('\t'):
            if section:
                try:
                    word, reading, headword = section.split(',')
                except ValueError:
                    word, reading, headword = section, None, section

                print(word, reading, headword, sep='\t')
                yield ParsedToken(word, reading, headword)


# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """ Map style classes to their user-configured inline versions. """

    for k, v in cfg.styles.items():
        txt = txt.replace(k, v)

    return txt


def update_html(html_notation: str) -> str:
    html_notation = convert_to_inline_style(html_notation)
    if cfg.pitch_accent.output_hiragana:
        html_notation = to_hiragana(html_notation)
    return html_notation


@functools.lru_cache(maxsize=cfg.cache_lookups)
def mecab_translate(expr: str) -> Tuple[ParsedToken, ...]:
    return tuple(mecab.translate(expr))


@functools.lru_cache(maxsize=cfg.cache_lookups)
def get_pronunciations(expr: str, sanitize=True, recurse=True) -> AccentDict:
    """
    Search pronunciations for a particular expression.

    Returns a dictionary mapping the expression (or sub-expressions contained in the expression)
    to a list of html-styled pronunciations.
    """

    ret = OrderedDict()

    # Sanitize input
    if sanitize:
        expr = htmlToTextLine(expr)
        sanitize = False

    # If the expression contains furigana, split it.
    expr, expr_reading = word_reading(expr)

    # Skip empty strings and user-specified blocklisted words
    if not expr or cfg.pitch_accent.is_blocklisted(expr):
        return ret

    # Sometimes furigana notation is being used by the users to distinguish otherwise duplicate notes.
    # E.g., テスト[1], テスト[2]
    # If there are multiple readings present, ignore all of them.
    if expr_reading and (expr_reading.isnumeric() or cfg.furigana.reading_separator in expr_reading):
        expr_reading = None

    if expr in acc_dict:
        ret.setdefault(expr, [])
        for entry in acc_dict[expr]:
            # if there's furigana, and it doesn't match the entry, skip.
            if expr_reading and to_katakana(entry.katakana_reading) != to_katakana(expr_reading):
                continue
            if entry not in ret[expr]:
                ret[expr].append(entry)
    elif (expr_katakana := to_katakana(expr)) in acc_dict and cfg.pitch_accent.kana_lookups:
        ret.update(get_pronunciations(expr_katakana, recurse=False))
    elif recurse:
        # Try to split the expression in various ways, and check if any of those results
        if len(split_expr := split_separators(expr)) > 1:
            for section in split_expr:
                ret.update(get_pronunciations(section, sanitize))

        # Only if lookups were not successful, we try splitting with Mecab
        if not ret and cfg.pitch_accent.use_mecab is True:
            for out in mecab_translate(expr):
                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-expression.
                ret.update(get_pronunciations(out.headword, sanitize, recurse=False))

                # If everything failed, try katakana lookups.
                # Katakana lookups are possible because of the additional key in the database.
                # If the word was in conjugated form, this lookup will also fail.
                if (
                        not ret.get(out.headword)
                        and out.katakana_reading
                        and cfg.pitch_accent.kana_lookups is True
                ):
                    ret.update(get_pronunciations(out.katakana_reading, sanitize, recurse=False))

    return ret


def iter_accents(word: str) -> Iterable[FormattedEntry]:
    if word in (accents := get_pronunciations(word, recurse=False)):
        for entry in accents[word]:
            yield entry


def get_notation(entry: FormattedEntry, mode: TaskMode) -> str:
    if mode == TaskMode.html:
        return update_html(entry.html_notation)
    if mode == TaskMode.number:
        return str(entry.pitch_number)
    raise Exception("Unreachable.")


def format_pronunciations(
        pronunciations: AccentDict,
        mode: TaskMode = TaskMode.html,
        sep_single: str = "・",
        sep_multi: str = "、",
        expr_sep: str = None
) -> str:
    ordered_dict = OrderedDict()
    for word, entries in pronunciations.items():
        ordered_dict[word] = sep_single.join(dict.fromkeys(get_notation(entry, mode) for entry in entries))

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join(f"{k}{expr_sep}{v}" for k, v in ordered_dict.items())
    else:
        txt = sep_multi.join(ordered_dict.values())

    return txt


def iter_furigana(out: ParsedToken) -> Iterable[str]:
    if out.katakana_reading:
        yield format_output(out.word, out.hiragana_reading)

    if cfg.furigana.can_lookup_db(out.headword):
        for entry in iter_accents(out.headword):
            reading = unify_repr(adjust_reading(out.word, out.headword, to_hiragana(entry.katakana_reading)))
            yield format_output(out.word, reading)


def format_furigana(out: ParsedToken) -> str:
    if is_kana_word(out.word) or cfg.furigana.is_blocklisted(out.word):
        return out.word
    elif readings := list(iter_furigana(out)):
        return mingle_readings(readings, sep=cfg.furigana.reading_separator) if len(readings) > 1 else readings[0]
    else:
        return out.word


def try_lookup_full_text(text: str) -> Optional[str]:
    """
    Try looking up whole text in the accent db.
    Avoids calling mecab when the text contains one word in dictionary form
    or multiple words in dictionary form separated by punctuation.
    """
    dummy = ParsedToken(text, None, text)
    furigana = format_furigana(dummy)
    return furigana if furigana != text else None


def generate_furigana(src_text) -> str:
    substrings = []
    for token in tokenize(src_text):
        if isinstance(token, ParseableToken):
            if furigana := try_lookup_full_text(token):
                substrings.append(furigana)
                continue
            for out in mecab_translate(token):
                substrings.append(format_furigana(out))
        else:
            substrings.append(token)

    return ''.join(substrings).strip()


# Tasks
##########################################################################


def can_fill_destination(note: Note, src_field: str, dst_field: str) -> bool:
    # Field names are empty or None
    if not src_field or not dst_field:
        return False

    # The note doesn't have fields with these names
    if src_field not in note or dst_field not in note:
        return False

    # Yomichan added `No pitch accent data` to the field when creating the note
    if "No pitch accent data".lower() in note[dst_field].lower():
        return True

    # Field is empty
    if len(htmlToTextLine(note[dst_field])) == 0:
        return True

    # Allowed regenerating regardless
    if cfg.regenerate_readings is True:
        return True

    return False


def do_task(note: Note, task: Task) -> bool:
    proceed = can_fill_destination(note, task.src_field, task.dst_field)
    src_text = mw.col.media.strip(note[task.src_field]).strip()
    changed = False
    if proceed and src_text:
        if task.mode == TaskMode.furigana:
            note[task.dst_field] = generate_furigana(src_text)
        else:
            note[task.dst_field] = format_pronunciations(get_pronunciations(src_text), mode=task.mode)
        changed = True
    return changed


def do_tasks(note: Note, tasks: Iterable[Task], changed: bool = False) -> bool:
    for task in tasks:
        changed = do_task(note, task) or changed
    return changed


def on_focus_lost(changed: bool, note: Note, field_idx: int) -> bool:
    return do_tasks(
        note=note,
        tasks=iter_tasks(note, src_field=note.keys()[field_idx]),
        changed=changed
    )


def should_generate(note: Note) -> bool:
    return (
            cfg.generate_on_note_add is True
            and mw.app.activeWindow() is None
            and note.id == 0
    )


def on_add_note(note: Note) -> None:
    if should_generate(note):
        do_tasks(note=note, tasks=iter_tasks(note))


# Entry point
##########################################################################

mecab = MecabController()
acc_dict = database_init()


def init():
    # Generate when editing a note

    if ANKI21_VERSION < 45:
        from anki.hooks import addHook
        addHook('editFocusLost', on_focus_lost)
    else:
        from aqt import gui_hooks

        gui_hooks.editor_did_unfocus_field.append(on_focus_lost)

    # Generate when AnkiConnect adds a new note
    collection_will_add_note.append(on_add_note)
