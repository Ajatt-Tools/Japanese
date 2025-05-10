# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *


def fix_default_anki_style(self: QTableWidget):
    from aqt import mw

    try:
        from aqt.theme import WidgetStyle
    except ImportError:
        # Running an old version of Anki. No action is necessary.
        return
    if mw.pm.get_widget_style() == WidgetStyle.ANKI:
        self.setStyleSheet("""
                QTableWidget,
                QTableView,
                QLineEdit,
                QHeaderView,
                QHeaderView::section,
                QHeaderView::section:last,
                QHeaderView::section:first,
                QHeaderView::section:only-one,
                QHeaderView::section:pressed {
                    font-size: 16px;
                    border-radius: 0px;
                    padding: 0px;
                }
                """)
