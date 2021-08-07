import functools
import re
from importlib.metadata import version
from typing import Dict, Any, List

from anki.notes import Note
from anki.utils import htmlToTextLine
from aqt import mw

ANKI21_VERSION = int(version('aqt').split('.')[-1])


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


def escape_text(text):
    # strip characters that trip up kakasi/mecab
    text = text.replace("\n", " ")
    text = text.replace(u'\uff5e', "~")
    text = re.sub("<br( /)?>", "---newline---", text)
    text = htmlToTextLine(text)
    text = text.replace("---newline---", "<br>")
    return text


def _split_separators():
    """
    Split text by common separators (like / or ・) into separate words that can
    be looked up.
    """
    # Ref: https://stackoverflow.com/questions/15033196/using-javascript-to-check-whether-a-string-contains-japanese-characters-includi/15034560#15034560
    non_jap_regex = re.compile(
        u'[^\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f\u4e00-\u9fff\u3400-\u4dbf]+',
        re.U
    )
    jp_sep_regex = re.compile(
        u'[・、※【】「」〒◎×〃゜『』《》〜〽。〄〇〈〉〓〔〕〖〗〘 〙〚〛〝〞〟〠〡〢〣〥〦〧〨〭〮〯〫〬〶〷〸〹〺〻〼〾〿]',
        re.U
    )

    def func(expr: str) -> List[str]:
        expr = htmlToTextLine(expr)
        # Replace all typical separators with a space
        expr = re.sub(non_jap_regex, ' ', expr)  # Remove non-Japanese characters
        expr = re.sub(jp_sep_regex, ' ', expr)  # Remove Japanese punctuation
        return expr.split(' ')

    return func


config = mw.addonManager.getConfig(__name__)
iter_fields = functools.partial(zip, config['srcFields'], config['dstFields'])
split_separators = _split_separators()
