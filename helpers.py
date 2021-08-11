# -*- coding: utf-8 -*-

import functools
import re
from typing import Dict, Any, List, Tuple, Optional

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


def get_notetype(note: Note) -> Dict[str, Any]:
    if hasattr(note, 'note_type'):
        return note.note_type()
    else:
        return note.model()


def is_supported_notetype(note: Note):
    # Check if this is a supported note type.

    if not config["noteTypes"]:
        # supported note types weren't specified by the user.
        # treat all note types as supported
        return True

    this_notetype = get_notetype(note)['name']
    return any(notetype.lower() in this_notetype.lower() for notetype in config["noteTypes"])


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


config = aqt.mw.addonManager.getConfig(__name__)
iter_fields = functools.partial(zip, config['srcFields'], config['dstFields'])
