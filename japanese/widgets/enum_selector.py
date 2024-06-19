# Copyright: (C) 2023 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import enum

from aqt.qt import *

from ..ajt_common.checkable_combobox import CheckableComboBox
from ..ajt_common.utils import ui_translate


class EnumSelectCombo(QComboBox):
    def __init__(
        self,
        enum_type: enum.EnumMeta,
        initial_value: Union[enum.Enum, str] = None,
        show_values: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        for item in enum_type:
            self.addItem(ui_translate(item.value if show_values else item.name), item)
        if initial_value is not None:
            self.setCurrentName(initial_value)

    def setCurrentName(self, name: Union[enum.Enum, str]):
        for index in range(self.count()):
            if self.itemData(index) == name or self.itemData(index).name == name:
                return self.setCurrentIndex(index)

    def currentName(self) -> str:
        return self.currentData().name

    def setCurrentText(self, text: str) -> None:
        raise NotImplementedError()

    def currentText(self) -> str:
        raise NotImplementedError()


class FlagSelectCombo(CheckableComboBox):
    def __init__(
        self,
        enum_type: enum.EnumMeta,
        parent=None,
    ):
        super().__init__(parent)
        self._enum_type = enum_type
        self._populate_options()

    def _populate_options(self):
        for flag_item in self._enum_type:
            self.addCheckableItem(ui_translate(flag_item.name), data=flag_item)

    def set_checked_flags(self, flags: enum.Flag) -> None:
        return self.setCheckedData(flags)

    def comma_separated_flags(self) -> str:
        """
        Used to serialize checked options to store them in json.
        """
        return ",".join(flag_item.name for flag_item in self.checkedData())
