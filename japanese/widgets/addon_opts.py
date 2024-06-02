# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Collection
from collections.abc import Iterable
from typing import Optional

from aqt import mw
from aqt.qt import *

from ..ajt_common.checkable_combobox import CheckableComboBox
from ..ajt_common.utils import ui_translate
from ..helpers.profiles import TaskCaller

NARROW_WIDGET_MAX_WIDTH = 96


class TriggeredBySelector(CheckableComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._populate_options()

    def _populate_options(self):
        for caller in TaskCaller:
            self.addCheckableItem(ui_translate(caller.name), caller)

    def set_enabled_callers(self, callers: Collection[TaskCaller]):
        return self.setCheckedData(callers)

    def comma_separated_callers(self):
        return ",".join(caller.name for caller in self.checkedData())


class WordsEdit(QTextEdit):
    _min_height = 32
    _font_size = 16

    def __init__(self, initial_values: list[str]):
        super().__init__()
        self.setAcceptRichText(False)
        self.set_values(initial_values)
        self.setMinimumHeight(self._min_height)
        self._adjust_font_size()
        self.setPlaceholderText("Comma-separated list of words...")

    def _adjust_font_size(self):
        font = self.font()
        font.setPixelSize(self._font_size)
        self.setFont(font)

    def set_values(self, values: list[str]):
        if values:
            self.setPlainText(",".join(dict.fromkeys(values)))

    def as_text(self) -> str:
        return ",".join(dict.fromkeys(filter(bool, self.toPlainText().replace(" ", "").split("\n"))))


class NarrowLineEdit(QLineEdit):
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setMaximumWidth(self._max_width)


class NarrowSpinBox(QSpinBox):
    _allowed_range: tuple[int, int] = (1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(
        self,
        initial_value: Optional[int] = None,
        allowed_range: Optional[tuple[int, int]] = None,
        *args,
    ) -> None:
        super().__init__(*args)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        if initial_value:
            self.setValue(initial_value)


class PxNarrowSpinBox(NarrowSpinBox):
    def __init__(
        self,
        initial_value: Optional[int] = None,
        allowed_range: Optional[tuple[int, int]] = None,
        *args,
    ) -> None:
        super().__init__(initial_value, allowed_range, *args)
        self.setSuffix(" px")


class PxDoubleNarrowSpinBox(QDoubleSpinBox):
    _allowed_range: tuple[float, float] = (1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH
    _decimals: int = 2

    def __init__(
        self,
        initial_value: Optional[float] = None,
        allowed_range: Optional[tuple[float, float]] = None,
        *args,
    ) -> None:
        super().__init__(*args)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        self.setDecimals(self._decimals)
        self.setSuffix(" px")
        if initial_value:
            self.setValue(initial_value)


class StrokeDisarrayLineEdit(NarrowLineEdit):
    """Only used to edit SVG devoiced stroke dasharray."""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        rx = QRegularExpression(r"^(\d )*\d$")
        validator = QRegularExpressionValidator(rx)
        self.setValidator(validator)


class EditableSelector(QComboBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setEditable(True)


def relevant_field_names(note_type_name_fuzzy: Optional[str] = None) -> Iterable[str]:
    """
    Return an iterable of field names present in note types whose names contain the first parameter.
    """
    assert mw
    for model in mw.col.models.all_names_and_ids():
        if not note_type_name_fuzzy or note_type_name_fuzzy.lower() in model.name.lower():
            for field in mw.col.models.get(model.id)["flds"]:
                yield field["name"]


class FieldNameSelector(EditableSelector):
    def __init__(self, initial_value: Optional[str] = None, *args):
        super().__init__(*args)
        self.clear()
        self.addItems(dict.fromkeys(relevant_field_names()))
        if initial_value:
            self.setCurrentText(initial_value)
