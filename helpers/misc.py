import re

from anki.media import MediaManager


def strip_media_tags(txt: str) -> str:
    """Return text with sound and image tags removed."""
    for reg in MediaManager.regexps:
        txt = re.sub(reg, "", txt)
    return txt
