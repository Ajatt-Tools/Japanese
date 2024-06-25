# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from ..ajt_common.enum_select_combo import EnumSelectCombo
from ..ajt_common.grab_key import ShortCutGrabButton
from ..widgets.addon_opts import WordsEdit
from .enum_selector import FlagSelectCombo


def as_config_dict(widgets: dict[str, QWidget]) -> dict[str, Union[bool, str, int]]:
    d = {}
    for key, widget in widgets.items():
        if isinstance(widget, FlagSelectCombo):
            d[key] = widget.comma_separated_flags()
        elif isinstance(widget, EnumSelectCombo):
            d[key] = widget.currentName()
        elif isinstance(widget, QComboBox):
            d[key] = widget.currentText()
        elif isinstance(widget, QLineEdit):
            d[key] = widget.text()
        elif isinstance(widget, QCheckBox):
            d[key] = widget.isChecked()
        elif isinstance(widget, ShortCutGrabButton):
            d[key] = widget.value()
        elif isinstance(widget, WordsEdit):
            d[key] = widget.as_text()
        elif isinstance(widget, QAbstractSpinBox):
            d[key] = widget.value()
        else:
            raise RuntimeError(f"Don't know how to handle widget of type {type(widget).__name__}.")
    return d
