# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum

from aqt.qt import *

from ..ajt_common.color_picker import ColorEditPicker
from ..ajt_common.enum_select_combo import EnumSelectCombo
from ..ajt_common.grab_key import ShortCutGrabButton
from ..widgets.addon_opts import WordsEdit
from .enum_selector import FlagSelectCombo


def set_from_cfg(widget: QWidget, value: Union[bool, str, int, float, enum.Enum]) -> None:
    """Set a widget's value from a configuration value based on the widget type."""
    if isinstance(widget, QDoubleSpinBox) and isinstance(value, (int, float)):
        widget.setValue(value)
    elif isinstance(widget, QSpinBox) and isinstance(value, int):
        widget.setValue(value)
    elif isinstance(widget, QLineEdit) and isinstance(value, str):
        widget.setText(value)
    elif isinstance(widget, QCheckBox) and isinstance(value, bool):
        widget.setChecked(value)
    elif isinstance(widget, EnumSelectCombo) and isinstance(value, (str, enum.Enum)):
        widget.setCurrentName(value)
    elif isinstance(widget, QComboBox) and isinstance(value, str):
        widget.setCurrentText(value)
    else:
        raise ValueError(
            f"Can't handle widget of type {type(widget).__name__} and value of type {type(value).__name__}"
        )


def change_event(widget: QWidget) -> pyqtBoundSignal:
    """Return the appropriate change signal for a widget based on its type."""
    if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
        return widget.valueChanged
    elif isinstance(widget, QLineEdit):
        return widget.textChanged
    elif isinstance(widget, QCheckBox):
        # checkStateChanged in pyqt 6.7+
        return widget.stateChanged
    elif isinstance(widget, QComboBox):
        return widget.currentIndexChanged
    else:
        raise ValueError("unknown type")


def get_from_widget(widget: QWidget) -> Union[bool, str, int, float]:
    """Extract the current value from a widget based on its type."""
    if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
        return widget.value()
    elif isinstance(widget, ColorEditPicker):
        return widget.color_hex()
    elif isinstance(widget, FlagSelectCombo):
        return widget.comma_separated_flags()
    elif isinstance(widget, EnumSelectCombo):
        return widget.currentName()
    elif isinstance(widget, QComboBox):
        return widget.currentText()
    elif isinstance(widget, QLineEdit):
        return widget.text()
    elif isinstance(widget, QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, ShortCutGrabButton):
        return widget.value()
    elif isinstance(widget, WordsEdit):
        return widget.as_text()
    else:
        raise ValueError(f"Don't know how to handle widget of type {type(widget).__name__}.")


def as_config_dict(widgets: dict[str, QWidget]) -> dict[str, Union[bool, str, int, float]]:
    return {key: get_from_widget(widget) for key, widget in widgets.items()}
