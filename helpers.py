# -*- coding: utf-8 -*-

import re
from typing import Dict, Any, List, Tuple, Optional, Set, Iterator

import aqt
from anki.notes import Note
from anki.utils import htmlToTextLine

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

config = aqt.mw.addonManager.getConfig(__name__)


def write_config():
    return aqt.mw.addonManager.writeConfig(__name__, config)


def iter_fields() -> Iterator[Tuple[str, str]]:
    return zip(config['source_fields'], config['destination_fields'])


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


def is_supported_notetype(note: Note) -> bool:
    # Check if this is a supported note type.

    if not (supported_note_types := config['note_types']):
        # Supported note types weren't specified by the user.
        # Treat all note types as supported.
        return True
    else:
        note_type_name = get_notetype(note)['name']
        return any(supported.lower() in note_type_name.lower() for supported in supported_note_types)


def escape_text(text: str) -> str:
    """Strip characters that trip up mecab."""
    text = text.replace("\n", " ")
    text = text.replace(u'\uff5e', "~")
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
