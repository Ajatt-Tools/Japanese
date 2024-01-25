# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.utils import html_to_text_line
from aqt import mw


def strip_html_and_media(text: str) -> str:
    return html_to_text_line(mw.col.media.strip(text))
