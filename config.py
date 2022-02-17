# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import aqt


def get_config():
    return aqt.mw.addonManager.getConfig(__name__)


def write_config():
    return aqt.mw.addonManager.writeConfig(__name__, config)


config = get_config()
