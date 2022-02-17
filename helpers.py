import enum
import re
from typing import Dict, Any, List, Tuple, Optional, Set, Iterator, NewType, NamedTuple

import aqt
from anki.notes import Note
from anki.utils import htmlToTextLine

try:
    from anki.notes import NoteId
except ImportError:
    NoteId = NewType("NoteId", int)

ANKI21_VERSION = int(aqt.appVersion.split('.')[-1])

NON_JP_REGEX = re.compile(
    # Reference: https://stackoverflow.com/questions/15033196/
    # Here I added `[` and `]` at the end to keep furigana notation.
    # Furigana notation is going to be parsed separately.
    r'[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf\[\]]+',
    re.U
)
JP_SEP_REGEX = re.compile(
    r'[・、※【】「」〒◎×〃゜『』《》〜〽。〄〇〈〉〓〔〕〖〗〘 〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿]',
    re.U
)


class TaskMode(enum.Enum):
    number = enum.auto()
    html = enum.auto()


class Task(NamedTuple):
    src_field: str
    dst_field: str
    mode: TaskMode


def get_config():
    return aqt.mw.addonManager.getConfig(__name__)


def write_config():
    return aqt.mw.addonManager.writeConfig(__name__, config)


def profile_matches(note_type: Dict[str, Any], profile: Dict[str, str]) -> bool:
    return profile['note_type'].lower() in note_type['name'].lower()


def iter_fields(note: Note) -> Iterator[Task]:
    note_type = get_notetype(note)
    for profile in config['profiles']:
        if profile_matches(note_type, profile):
            yield Task(profile['source'], profile['destination'], TaskMode[profile['mode']])


def ui_translate(key: str) -> str:
    return key.capitalize().replace('_', ' ')


def get_notetype(note: Note) -> Dict[str, Any]:
    if hasattr(note, 'note_type'):
        return note.note_type()
    else:
        return note.model()


def all_note_type_names():
    return (note_type.name for note_type in aqt.mw.col.models.all_names_and_ids())


def all_note_type_field_names() -> Set[str]:
    fields = set()
    for model in aqt.mw.col.models.all():
        fields.update(field['name'] for field in model.get('flds'))

    return fields


def escape_text(text: str) -> str:
    """Strip characters that trip up mecab."""
    text = text.replace("\n", " ")
    text = text.replace('\uff5e', "~")
    text = re.sub("<br( /)?>", "---newline---", text)
    text = htmlToTextLine(text)
    text = text.replace("---newline---", "<br>")
    return text


def split_separators(expr: str) -> List[str]:
    """
    Split text by common separators (like / or ・) into separate words that can
    be looked up.
    """

    expr = htmlToTextLine(expr)
    # Replace all typical separators with a space
    expr = re.sub(NON_JP_REGEX, ' ', expr)  # Remove non-Japanese characters
    expr = re.sub(JP_SEP_REGEX, ' ', expr)  # Remove Japanese punctuation
    return expr.split(' ')


def split_furigana(expr: str) -> Tuple[str, Optional[str]]:
    """
    Parses expr.
    Outputs (word, reading) if the expr is formatted as word[reading].
    If not, outputs (expr, None).
    """
    if match := re.search(r'^\s*(?P<word>[^\s\[\]]+)\[(?P<reading>[^\s\[\]]+)](?P<suffix>[^\s\[\]]*)\s*$', expr):
        return match.group('word') + match.group('suffix'), match.group('reading') + match.group('suffix')
    else:
        return expr, None


config = get_config()
