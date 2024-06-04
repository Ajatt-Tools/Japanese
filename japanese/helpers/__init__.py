# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

try:
    # Running as add-on.
    from ..ajt_common.consts import ADDON_SERIES
except ImportError:
    # Running as a standalone script.
    ADDON_SERIES = "TEST"

LONG_VOWEL_MARK: str = "ー"
ADDON_NAME: str = f"{ADDON_SERIES} Japanese"
THIS_ADDON_MODULE: str = __name__.split(".")[0]
