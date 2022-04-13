# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import dataclasses
import enum
from types import SimpleNamespace
from typing import Optional, Iterable, Dict, Tuple, List

from aqt import mw
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom

from .ajt_common import menu_root_entry, tweak_window, ShortCutGrabButton, ADDON_SERIES
from .config_view import ConfigViewBase, config_view as cfg
from .helpers import ui_translate
from .helpers.config import write_config
from .helpers.mingle_readings import WordWrapMode
from .helpers.profiles import TaskMode, Profile, iter_profiles

EDIT_MIN_WIDTH = 100


def adjust_to_contents(widget: QWidget):
    try:
        widget.setSizeAdjustPolicy(widget.AdjustToContents)
    except AttributeError:
        pass


class ControlPanel(QHBoxLayout):
    def __init__(self, *args):
        super().__init__(*args)
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.clone_btn = QPushButton("Clone")
        self.addWidget(self.add_btn)
        self.addWidget(self.remove_btn)
        self.addWidget(self.clone_btn)


def relevant_field_names(note_type_name_fuzzy: Optional[str]) -> Iterable[str]:
    """
    Return an iterable of field names present in note types whose names contain the first parameter.
    """
    for model in mw.col.models.all_names_and_ids():
        if not note_type_name_fuzzy or note_type_name_fuzzy.lower() in model.name.lower():
            for field in mw.col.models.get(model.id)['flds']:
                yield field['name']


class EditableSelector(QComboBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setEditable(True)


class NoteTypeSelector(EditableSelector):
    def repopulate(self, current_text: Optional[str]):
        self.clear()
        self.addItems([n.name for n in mw.col.models.all_names_and_ids()])
        if current_text:
            self.setCurrentText(current_text)
        elif self.count() > 0:
            self.setCurrentIndex(0)


class EnumSelector(QComboBox):
    @property
    def _type(self) -> enum.EnumMeta:
        raise NotImplementedError()

    def __init__(self, initial_value: Optional[enum.Enum] = None, *args):
        super().__init__(*args)
        self.addItems(mode.name.capitalize() for mode in self._type)
        if initial_value is not None:
            self.setCurrentText(initial_value.name)

    def setCurrentText(self, text: str):
        return super().setCurrentText(text.capitalize())

    def currentText(self) -> str:
        return super().currentText().lower()


class ModeSelector(EnumSelector):
    _type = TaskMode


class WrapSelector(EnumSelector):
    _type = WordWrapMode


def as_config_dict(widgets: Dict[str, QWidget]) -> Dict[str, Union[bool, str, int]]:
    d = {}
    for key, widget in widgets.items():
        if isinstance(widget, QComboBox):
            d[key] = widget.currentText()
        elif isinstance(widget, QLineEdit):
            d[key] = widget.text()
        elif isinstance(widget, QCheckBox):
            d[key] = widget.isChecked()
        elif isinstance(widget, ShortCutGrabButton):
            d[key] = widget.value()
        elif isinstance(widget, WordsEdit):
            d[key] = widget.as_text()
        elif isinstance(widget, QSpinBox):
            d[key] = widget.value()
        else:
            raise RuntimeError(f"Don't know how to handle widget of type {type(widget).__name__}.")
    return d


class ProfileList(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Profiles")
        self.setCheckable(False)
        self._list_widget = QListWidget()
        self._control_panel = ControlPanel()
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        self.setLayout(self.make_layout())
        self._setup_signals()
        adjust_to_contents(self._list_widget)

    def current_item(self) -> QListWidgetItem:
        return self._list_widget.currentItem()

    def profiles(self) -> Iterable[Profile]:
        for idx in range(self._list_widget.count()):
            yield self._list_widget.item(idx).data(Qt.UserRole)

    def _setup_signals(self):
        self.current_item_changed = self._list_widget.currentItemChanged
        qconnect(self._control_panel.add_btn.clicked, self.add_profile)
        qconnect(self._control_panel.remove_btn.clicked, self.remove_current)
        qconnect(self._control_panel.clone_btn.clicked, self.clone_profile)

    def add_profile(self):
        self.add_and_select(Profile.new())

    def remove_current(self) -> Optional[int]:
        if (current := self.current_item()) and current.isSelected():
            self._list_widget.takeItem(row := self._list_widget.currentRow())
            return row

    def clone_profile(self):
        if (current := self.current_item()) and current.isSelected():
            self.add_and_select(Profile.clone(current.data(Qt.UserRole)))

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addWidget(self._list_widget)
        layout.addLayout(self._control_panel)
        return layout

    def populate(self, profiles: Iterable[Profile]):
        self._list_widget.clear()
        for profile in profiles:
            item = QListWidgetItem()
            item.setText(profile.name)
            item.setData(Qt.UserRole, profile)
            self._list_widget.addItem(item)
        self._list_widget.setCurrentRow(0)

    def add_and_select(self, profile: Profile):
        count = self._list_widget.count()
        item = QListWidgetItem()
        item.setText(profile.name)
        item.setData(Qt.UserRole, profile)
        self._list_widget.addItem(item)
        self._list_widget.setCurrentRow(count)


class ProfileEditForm(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Edit Profile")
        self.setCheckable(False)
        self._form = SimpleNamespace(
            name=QLineEdit(),
            note_type=NoteTypeSelector(),
            source=EditableSelector(),
            destination=EditableSelector(),
            mode=ModeSelector(),
        )
        self.setLayout(self.make_layout())
        adjust_to_contents(self)
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        qconnect(self._form.note_type.currentIndexChanged, lambda index: self.repopulate_fields())

    def as_dict(self) -> Dict[str, str]:
        return as_config_dict(self._form.__dict__)

    def data(self) -> Profile:
        return Profile(**self.as_dict())

    def make_layout(self) -> QLayout:
        layout = QFormLayout()
        for key, widget in self._form.__dict__.items():
            layout.addRow(ui_translate(key), widget)
        return layout

    def load_profile(self, profile: Profile):
        self._form.name.setText(profile.name)
        self._form.mode.setCurrentText(profile.mode)
        self._form.note_type.repopulate(profile.note_type)
        self.repopulate_fields(profile)

    def repopulate_fields(self, profile: Optional[Profile] = None):
        for key in ('source', 'destination',):
            widget: QComboBox = self._form.__dict__[key]
            current_text = dataclasses.asdict(profile)[key] if profile else widget.currentText()
            widget.clear()
            widget.addItems(dict.fromkeys(relevant_field_names(self._form.note_type.currentText())))
            widget.setCurrentText(current_text)


class ProfileEdit(QHBoxLayout):
    def __init__(self, profiles: Iterable[Profile], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._left_panel = ProfileList()
        self._right_panel = ProfileEditForm()
        self.addWidget(self._left_panel)
        self.addWidget(self._right_panel)
        qconnect(self._left_panel.current_item_changed, self._edit_profile)
        self._left_panel.populate(profiles)

    def _edit_profile(self, current: QListWidgetItem, previous: QListWidgetItem):
        self._apply_profile(previous)
        if current:
            self._right_panel.setEnabled(True)
            self._right_panel.load_profile(current.data(Qt.UserRole))
        else:
            self._right_panel.setEnabled(False)

    def _apply_profile(self, item: QListWidgetItem):
        if item:
            profile = self._right_panel.data()
            item.setData(Qt.UserRole, profile)
            item.setText(profile.name)

    def as_list(self) -> List[Dict[str, str]]:
        self._apply_profile(self._left_panel.current_item())
        return [dataclasses.asdict(p) for p in self._left_panel.profiles()]


class WordsEdit(QTextEdit):
    def __init__(self, initial_values: List[str], *args):
        super().__init__(*args)
        self.setAcceptRichText(False)
        if initial_values:
            self.set_values(initial_values)

    def set_values(self, values: List[str]):
        self.setPlainText(','.join(dict.fromkeys(values)))

    def as_text(self) -> str:
        return ','.join(dict.fromkeys(filter(bool, self.toPlainText().replace(' ', '').split('\n'))))


class SettingsForm(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle(self._title)
        self.setCheckable(False)
        self._widgets = SimpleNamespace(**dict(self._create_checkboxes()))
        self._add_widgets()
        self.setLayout(self._make_layout())

    @property
    def _title(self) -> str:
        raise NotImplementedError()

    @property
    def _config(self) -> ConfigViewBase:
        raise NotImplementedError()

    def as_dict(self) -> Dict[str, Union[bool, str, int]]:
        return as_config_dict(self._widgets.__dict__)

    def _create_checkboxes(self) -> Iterable[Tuple[str, QCheckBox]]:
        for key, value in self._config.bools():
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

    def _add_widgets(self):
        pass


class GeneralSettingsForm(SettingsForm):
    _title = "General"
    _config = cfg


class PitchSettingsForm(SettingsForm):
    _title = "Pitch Options"
    _config = cfg.pitch_accent

    def _add_widgets(self):
        max_results = QSpinBox()
        max_results.setRange(1, 99)
        max_results.setValue(self._config.maximum_results)
        self._widgets.maximum_results = max_results
        self._widgets.reading_separator = QLineEdit(self._config.reading_separator)
        self._widgets.word_separator = QLineEdit(self._config.word_separator)
        self._widgets.lookup_shortcut = ShortCutGrabButton(initial_value=self._config.lookup_shortcut)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)


class FuriganaSettingsForm(SettingsForm):
    _title = "Furigana Options"
    _config = cfg.furigana

    def _add_widgets(self):
        max_results = QSpinBox()
        max_results.setRange(1, 99)
        max_results.setValue(self._config.maximum_results)
        self._widgets.maximum_results = max_results

        self._widgets.wrap_readings = WrapSelector(initial_value=self._config.wrap_readings)
        self._widgets.reading_separator = QLineEdit(self._config.reading_separator)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)
        self._widgets.mecab_only = WordsEdit(initial_values=self._config.mecab_only)


class ContextMenuSettingsForm(SettingsForm):
    _title = "Context menu"
    _config = cfg.context_menu


class ToolbarButtonSettingsForm(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setCheckable(True)
        self._shortcut_edit = ShortCutGrabButton()
        self._label_edit = QLineEdit()
        self.setLayout(self._make_layout())
        self._pass_methods()

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        layout.addRow("Shortcut", self._shortcut_edit)
        layout.addRow("Label", self._label_edit)
        return layout

    def _pass_methods(self):
        self.setText = self._label_edit.setText
        self.setShortcut = self._shortcut_edit.setValue

    def as_dict(self) -> Dict[str, Union[bool, str]]:
        return {
            "enabled": self.isChecked(),
            "shortcut": self._shortcut_edit.value(),
            "text": self._label_edit.text(),
        }


class ToolbarSettingsForm(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Toolbar")
        self.setCheckable(False)
        self._widgets = {}
        self._add_widgets()
        self.setLayout(self._make_layout())

    def _add_widgets(self):
        for key, button_config in cfg.toolbar.all():
            widget = ToolbarButtonSettingsForm()
            widget.setTitle(ui_translate(key))
            widget.setChecked(button_config.enabled)
            widget.setShortcut(button_config.shortcut)
            widget.setText(button_config.text)
            self._widgets[key] = widget

    def _make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        for key, widget in self._widgets.items():
            layout.addWidget(widget)
        return layout

    def as_dict(self) -> Dict[str, Dict[str, Union[str, bool]]]:
        return {
            key: widget.as_dict()
            for key, widget in self._widgets.items()
        }


class SettingsDialog(QDialog):
    name = 'Japanese Options'

    def __init__(self, *args):
        super().__init__(*args)
        self._profile_layout = ProfileEdit(profiles=iter_profiles())
        self._general_settings = GeneralSettingsForm()
        self._pitch_settings = PitchSettingsForm()
        self._furigana_settings = FuriganaSettingsForm()
        self._context_menu_settings = ContextMenuSettingsForm()
        self._toolbar_settings = ToolbarSettingsForm()
        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._setup_ui()
        restoreGeom(self, self.name, adjustSize=True)
        self.exec()
        saveGeom(self, self.name)

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(f'{ADDON_SERIES} {self.name}')
        self.setMinimumSize(800, 600)
        tweak_window(self)
        self.setLayout(self.make_layout())
        self.connect_widgets()

    def connect_widgets(self):
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addLayout(self._profile_layout)
        layout.addLayout(self.make_bottom_row())
        layout.addStretch()
        layout.addWidget(self._button_box)
        return layout

    def make_bottom_row(self) -> QLayout:
        layout = QGridLayout()
        # row, column, rowSpan, columnSpan
        layout.addWidget(self._general_settings, 1, 1)
        layout.addWidget(self._context_menu_settings, 2, 1)
        layout.addWidget(self._furigana_settings, 1, 2, 2, 1)
        layout.addWidget(self._pitch_settings, 1, 3, 2, 1)
        layout.addWidget(self._toolbar_settings, 1, 4, 2, 1)
        for column in (1, 2, 3):
            layout.setColumnStretch(column, 1)
        return layout

    def accept(self) -> None:
        from .helpers.config import config
        config.update(self._general_settings.as_dict())
        config['pitch_accent'].update(self._pitch_settings.as_dict())
        config['furigana'].update(self._furigana_settings.as_dict())
        config['context_menu'].update(self._context_menu_settings.as_dict())
        config['toolbar'].update(self._toolbar_settings.as_dict())
        config['profiles'] = self._profile_layout.as_list()
        write_config()
        QDialog.accept(self)


def init():
    root_menu = menu_root_entry()
    menu_action = QAction(f'{SettingsDialog.name}...', root_menu)
    qconnect(menu_action.triggered, lambda: SettingsDialog(mw))
    root_menu.addAction(menu_action)
