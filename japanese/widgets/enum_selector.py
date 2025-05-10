# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum

from ..ajt_common.checkable_combobox import CheckableComboBox
from ..ajt_common.utils import ui_translate
from ..helpers.consts import CFG_WORD_SEP


class FlagSelectCombo(CheckableComboBox):
    def __init__(self, enum_type: enum.EnumMeta, parent=None) -> None:
        super().__init__(parent)
        self._enum_type = enum_type
        self._populate_options()

    def _populate_options(self) -> None:
        for flag_item in self._enum_type:
            self.addCheckableItem(ui_translate(flag_item.name), data=flag_item)

    def set_checked_flags(self, flags: enum.Flag) -> None:
        return self.setCheckedData(flags)

    def comma_separated_flags(self) -> str:
        """
        Used to serialize checked options to store them in json.
        """
        return CFG_WORD_SEP.join(flag_item.name for flag_item in self.checkedData())
