import functools
from collections import OrderedDict

import anki.collection
from anki.hooks import wrap
from aqt import mw

from .config import config
from .database import AccentDict, FormattedEntry
from .database import init as database_init
from .helpers import *
from .mecab_controller import BasicMecabController
from .mecab_controller import to_hiragana, to_katakana


# Mecab controller
##########################################################################

class WordReading(NamedTuple):
    word: str
    katakana_reading: Optional[str]


class MecabController(BasicMecabController):
    _add_mecab_args = [
        '--node-format=%f[6],%f[7] ',
        '--unk-format=%m ',
        '--eos-format=\n',
    ]

    def __init__(self):
        super().__init__(mecab_args=self._add_mecab_args)

    def translate(self, expr: str) -> List[WordReading]:
        """ Returns dictionary form and its reading for each word in expr. """
        ret = []
        for section in self.run(escape_text(expr)).split():
            if len(split := section.split(',')) > 1:
                word, katakana = split
            else:
                word, katakana = split[0], None
            ret.append(WordReading(word, katakana))
        return ret


# Lookup
##########################################################################


def convert_to_inline_style(txt: str) -> str:
    """ Map style classes to their user-configured inline versions. """

    for k, v in config["styles"].items():
        txt = txt.replace(k, v)

    return txt


def get_skip_words() -> List[str]:
    """Returns a user-defined list of blocklisted words."""
    return re.split(r'[、, ]+', config['skip_words'], flags=re.IGNORECASE)


def should_skip(word: str) -> bool:
    """Returns True if the user specified that the word should not be looked up."""
    return to_katakana(word) in map(to_katakana, get_skip_words())


def update_html(entry: FormattedEntry) -> FormattedEntry:
    html_notation = convert_to_inline_style(entry.html_notation)
    if config['use_hiragana']:
        html_notation = to_hiragana(html_notation)
    return FormattedEntry(entry.katakana_reading, html_notation, entry.pitch_number)


@functools.lru_cache(maxsize=config['cache_lookups'])
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

    # If the expression contains furigana, split it.
    expr, expr_reading = split_furigana(expr)

    # Skip empty strings and user-specified blocklisted words
    if not expr or should_skip(expr):
        return ret

    if expr in acc_dict:
        styled_prons = []

        for entry in acc_dict[expr]:
            # if there's furigana, and it doesn't match the entry, skip.
            if expr_reading and to_katakana(entry.katakana_reading) != to_katakana(expr_reading):
                continue

            if (entry := update_html(entry)) not in styled_prons:
                styled_prons.append(entry)

        ret[expr] = styled_prons

    elif recurse:
        # Try to split the expression in various ways, and check if any of those results
        if len(split_expr := split_separators(expr)) > 1:
            for section in split_expr:
                ret.update(get_pronunciations(section, sanitize))

        # Only if lookups were not successful, we try splitting with Mecab
        if not ret and config['use_mecab'] is True:
            for word, katakana in mecab.translate(expr):
                # Avoid infinite recursion by saying that we should not try
                # Mecab again if we do not find any matches for this sub-expression.
                ret.update(get_pronunciations(word, sanitize, False))

                # If everything failed, try katakana lookups.
                # Katakana lookups are possible because of the additional key in the database.
                if (
                        not ret.get(word)
                        and katakana
                        and config['kana_lookups'] is True
                        and not should_skip(katakana)
                        and not should_skip(word)
                ):
                    ret.update(get_pronunciations(katakana, sanitize, False))

    return ret


def get_notation(entry: FormattedEntry, mode: TaskMode) -> str:
    return {
        TaskMode.html: entry.html_notation,
        TaskMode.number: entry.pitch_number
    }[mode]


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


# Pitch generation
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
    if config['regenerate_readings'] is True:
        return True

    return False


def do_task(note: Note, task: Task) -> bool:
    proceed = can_fill_destination(note, task.src_field, task.dst_field)
    src_text = mw.col.media.strip(note[task.src_field]).strip()
    changed = False
    if proceed and src_text:
        result: AccentDict = get_pronunciations(src_text)
        note[task.dst_field] = format_pronunciations(result, mode=task.mode)
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


def should_add_pitch_accents(note: Note) -> bool:
    return (
            config['generate_on_note_add'] is True
            and mw.app.activeWindow() is None
            and note.id == 0
    )


def on_add_note(_col, note: Note, _did) -> None:
    if should_add_pitch_accents(note):
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
    anki.collection.Collection.add_note = wrap(anki.collection.Collection.add_note, on_add_note, 'before')
