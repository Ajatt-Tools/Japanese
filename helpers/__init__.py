import re
from typing import NewType, List

import aqt
from anki.utils import htmlToTextLine

try:
    from anki.notes import NoteId
except ImportError:
    NoteId = NewType("NoteId", int)

ANKI21_VERSION = int(aqt.appVersion.split('.')[-1])
RE_FLAGS = re.MULTILINE | re.IGNORECASE
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


def ui_translate(key: str) -> str:
    return key.capitalize().replace('_', ' ')


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


def clean_furigana(expr: str) -> str:
    return re.sub(r'([^ \[\]]+)\[[^ \[\]]+]', r'\g<1>', expr, flags=RE_FLAGS).replace(' ', '')
