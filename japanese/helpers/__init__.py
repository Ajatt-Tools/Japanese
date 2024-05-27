# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    # Running as add-on.
    from ..ajt_common.consts import ADDON_SERIES
except ImportError:
    # Running as a standalone script.
    ADDON_SERIES = "TEST"

LONG_VOWEL_MARK = "ー"
ADDON_NAME = f"{ADDON_SERIES} Japanese"
