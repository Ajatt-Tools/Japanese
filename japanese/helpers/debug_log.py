# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import logging

from aqt import mw
from aqt.addons import AddonManager


def get_logger() -> logging.Logger:
    """Return Anki's add-on logger with messages visible by default."""
    logger = AddonManager.get_logger(__name__)
    logger.setLevel(logging.DEBUG)
    if not mw and not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    return logger
