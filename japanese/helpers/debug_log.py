# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import logging

from aqt import mw
from aqt.addons import AddonManager


def get_logger() -> logging.Logger:
    """Return Anki's add-on logger with messages visible by default.

    The level is set to DEBUG so diagnostic messages are not dropped.
    Outside Anki (tests, playground), where Anki's log handler is absent,
    a stderr StreamHandler is attached and propagation is disabled so
    messages are not duplicated under logging.basicConfig() or pytest.
    """
    logger = AddonManager.get_logger(__name__)
    logger.setLevel(logging.DEBUG)
    if not mw and not logger.handlers:
        logger.addHandler(logging.StreamHandler())
        logger.propagate = False
    return logger
