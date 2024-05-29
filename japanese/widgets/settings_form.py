# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from types import SimpleNamespace
from typing import Optional
from collections.abc import Iterable

from aqt.qt import *

from .widgets_to_config_dict import as_config_dict
from ..ajt_common.addon_config import ConfigSubViewBase
from ..ajt_common.utils import ui_translate


class SettingsForm(QWidget):
    _title: Optional[str] = None
    _config: Optional[ConfigSubViewBase] = None

    def __init__(self, *args):
        super().__init__(*args)
        assert self._title, "Title must be set."
        assert self._config, "Config must be set."

        self._widgets = SimpleNamespace()
        self._add_widgets()
        self._add_tooltips()
        self.setLayout(self._make_layout())

    @property
    def title(self) -> str:
        assert self._title
        return self._title

    def _add_widgets(self):
        """Subclasses add new widgets here."""
        self._widgets.__dict__.update(self._create_checkboxes())

    def _add_tooltips(self):
        """Subclasses add new tooltips here."""
        pass

    def as_dict(self) -> dict[str, Union[bool, str, int]]:
        return as_config_dict(self._widgets.__dict__)

    def _create_checkboxes(self) -> Iterable[tuple[str, QCheckBox]]:
        assert self._config
        for key, value in self._config.toggleables():
            checkbox = QCheckBox(ui_translate(key))
            checkbox.setChecked(value)
            yield key, checkbox

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        for key, widget in self._widgets.__dict__.items():
            if isinstance(widget, QCheckBox):
                layout.addRow(widget)
            else:
                layout.addRow(ui_translate(key), widget)
        return layout
