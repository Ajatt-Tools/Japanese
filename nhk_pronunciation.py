# -*- coding: utf-8 -*-

from collections import OrderedDict
from typing import Optional

from anki import hooks

from .database import init as database_init
from .helpers import *
from .mecab_controller import BasicMecabController
from .mecab_controller import to_hiragana


# Mecab controller
##########################################################################


class MecabController(BasicMecabController):
    _add_mecab_args = [
        '--node-format=%f[6],%f[7] ',
        '--unk-format=%m ',
        '--eos-format=\n',
    ]

    def __init__(self):
        super().__init__(mecab_args=self._add_mecab_args)

    def dict_forms(self, expr: str) -> List[str]:
        """ Returns dictionary form for each word in expr. """
        return self.run(escape_text(expr)).split()


# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """ Map style classes to their inline version """

    for k, v in config["styles"].items():
        txt = txt.replace(k, v)

    return txt


def get_pronunciations(expr: str, sanitize=True, recurse=True) -> OrderedDict[str, List[str]]:
    """
    Search pronuncations for a particular expression

    Returns a dictionary mapping the expression (or sub-expressions contained
    in the expression) to a list of html-styled pronunciations.
    """

    # Sanitize input
    if sanitize:
        expr = htmlToTextLine(expr)

    ret = OrderedDict()
    if expr in acc_dict:
        styled_prons = []

        for kana, pron in acc_dict[expr]:
            inline_pron = convert_to_inline_style(pron)

            if config["pronunciationHiragana"]:
                inline_pron = to_hiragana(inline_pron)

            if inline_pron not in styled_prons:
                styled_prons.append(inline_pron)

        ret[expr] = styled_prons
    elif recurse:
        # Try to split the expression in various ways, and check if any of those results
        split_expr = split_separators(expr)

        if len(split_expr) > 1:
            for expr in split_expr:
                ret.update(get_pronunciations(expr, sanitize))

        # Only if lookups were not successful, we try splitting with Mecab
        if not ret and config.get('useMecab') is True:
            for sub_expr in mecab.dict_forms(expr):
                kanji, katakana = sub_expr.split(',')

                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-expression.
                ret.update(get_pronunciations(kanji, sanitize, False))
                if not ret and config.get('kanaLookups') is True:
                    ret.update(get_pronunciations(to_hiragana(katakana), sanitize, False))

    return ret


def get_formatted_pronunciations(expr: str, sep_single="・", sep_multi="、", expr_sep=None, sanitize=True):
    pronunciations = get_pronunciations(expr, sanitize)

    single_merge = OrderedDict()
    for k, v in pronunciations.items():
        single_merge[k] = sep_single.join(v)

    # expr_sep is used to separate entries on lookup
    if expr_sep:
        txt = sep_multi.join([f"{k}{expr_sep}{v}" for k, v in single_merge.items()])
    else:
        txt = sep_multi.join(single_merge.values())

    return txt


# Pitch generation
##########################################################################

def find_dest_field_name(src_field_name: str) -> Optional[str]:
    for src, dest in iter_fields():
        if src_field_name == src:
            return dest
    else:
        return None


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

    # Allowed to regenerate regardless
    if config["regenerateReadings"] is True:
        return True

    return False


def fill_destination(note: Note, src_field: str, dst_field: str) -> bool:
    if not can_fill_destination(note, src_field, dst_field):
        return False

    # grab source text and update note
    if src_text := mw.col.media.strip(note[src_field]).strip():
        note[dst_field] = get_formatted_pronunciations(src_text)
        return True

    return False


def on_focus_lost(changed: bool, note: Note, field_idx: int) -> bool:
    # This notetype name is not included in the config file
    if not is_supported_notetype(note):
        return changed

    src_field = note.keys()[field_idx]
    dst_field = find_dest_field_name(src_field)

    return True if fill_destination(note, src_field, dst_field) else changed


def on_note_will_flush(note: Note) -> None:
    if config["generateOnNoteFlush"] is False:
        return

    # only accept calls when add cards dialog or anki browser are not open.
    # otherwise this function conflicts with add_pronunciation_focusLost which is called on 'editFocusLost'
    if mw.app.activeWindow() is not None:
        return

    if not is_supported_notetype(note):
        return

    for src_field, dst_field in iter_fields():
        fill_destination(note, src_field, dst_field)


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
    hooks.note_will_flush.append(on_note_will_flush)
