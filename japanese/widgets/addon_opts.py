# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Collection

from aqt.qt import *

from ..ajt_common.checkable_combobox import CheckableComboBox
from ..ajt_common.utils import ui_translate
from ..helpers.profiles import TaskCaller


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
