# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import dataclasses
from types import SimpleNamespace
from typing import Optional, Iterable, Dict, Tuple, List

from aqt import mw
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom, openLink

from .widgets.enum_selector import EnumSelectCombo
from .ajt_common.about_menu import tweak_window, menu_root_entry
from .ajt_common.consts import ADDON_SERIES
from .ajt_common.grab_key import ShortCutGrabButton
from .config_view import config_view as cfg, ReadingsDiscardMode
from .database import UserDb
from .helpers import ui_translate, split_list
from .helpers.profiles import Profile, ProfileFurigana, ProfilePitch, PitchOutputFormat
from .reading import acc_dict
from .widgets.pitch_override import PitchOverrideWidget

EDIT_MIN_WIDTH = 100
NARROW_WIDGET_MAX_WIDTH = 64
EXAMPLE_DECK_ANKIWEB_URL = "https://ankiweb.net/shared/info/1557722832"


def adjust_to_contents(widget: QWidget):
    try:
        widget.setSizeAdjustPolicy(widget.AdjustToContents)  # type: ignore
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


def as_config_dict(widgets: dict[str, QWidget]) -> dict[str, Union[bool, str, int]]:
    d = {}
    for key, widget in widgets.items():
        if isinstance(widget, EnumSelectCombo):
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
        elif isinstance(widget, QSpinBox):
            d[key] = widget.value()
        else:
            raise RuntimeError(f"Don't know how to handle widget of type {type(widget).__name__}.")
    return d


class ProfileList(QGroupBox):
    def __init__(self, profile_class: type(Profile), *args):
        super().__init__(*args)
        self.setTitle("Profiles")
        self.setCheckable(False)
        self._store_type = profile_class
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
            yield self._list_widget.item(idx).data(Qt.ItemDataRole.UserRole)

    def _setup_signals(self):
        self.current_item_changed = self._list_widget.currentItemChanged
        qconnect(self._control_panel.add_btn.clicked, self.add_profile)
        qconnect(self._control_panel.remove_btn.clicked, self.remove_current)
        qconnect(self._control_panel.clone_btn.clicked, self.clone_profile)

    def add_profile(self):
        self.add_and_select(self._store_type.new())

    def remove_current(self) -> Optional[int]:
        if (current := self.current_item()) and current.isSelected():
            self._list_widget.takeItem(row := self._list_widget.currentRow())
            return row

    def clone_profile(self):
        if (current := self.current_item()) and current.isSelected():
            self.add_and_select(Profile.clone(current.data(Qt.ItemDataRole.UserRole)))

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addWidget(self._list_widget)
        layout.addLayout(self._control_panel)
        return layout

    def populate(self):
        self._list_widget.clear()
        for profile in cfg.iter_profiles():
            if isinstance(profile, self._store_type):
                self.add_and_select(profile)
        self._list_widget.setCurrentRow(0)

    def add_and_select(self, profile: Profile):
        count = self._list_widget.count()
        item = QListWidgetItem()
        item.setText(profile.name)
        item.setData(Qt.ItemDataRole.UserRole, profile)
        self._list_widget.addItem(item)
        self._list_widget.setCurrentRow(count)


class ProfileEditForm(QGroupBox):
    _subclasses_map = {}  # e.g. ProfileFurigana => FuriganaProfileEditForm

    def __init_subclass__(cls, **kwargs):
        profile_class: type(Profile) = kwargs.pop('profile_class')  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[profile_class] = cls

    def __new__(cls, profile_class: type(Profile), *args, **kwargs):
        subclass = cls._subclasses_map[profile_class]
        return QGroupBox.__new__(subclass)

    def __init__(self, profile_class: type(Profile), *args):
        super().__init__(*args)
        self._profile_class = profile_class
        self.setTitle("Edit Profile")
        self.setCheckable(False)
        self._form = SimpleNamespace(
            name=QLineEdit(),
            note_type=NoteTypeSelector(),
            source=EditableSelector(),
            destination=EditableSelector(),
            split_morphemes=QCheckBox(),
        )
        self._expand_form()
        self._last_used_profile: Optional[Profile] = None
        self.setLayout(self._make_layout())
        adjust_to_contents(self)
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        qconnect(self._form.note_type.currentIndexChanged, lambda index: self._repopulate_fields())

    def _expand_form(self):
        """Subclasses add new widgets here."""
        pass

    def as_profile(self) -> Profile:
        return Profile(**self._as_dict())

    def load_profile(self, profile: Profile):
        self._last_used_profile = profile
        self._form.name.setText(profile.name)
        self._form.note_type.repopulate(profile.note_type)
        self._form.split_morphemes.setChecked(profile.split_morphemes)
        self._repopulate_fields(profile)

    def _as_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self._last_used_profile) | as_config_dict(self._form.__dict__)

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        for key, widget in self._form.__dict__.items():
            layout.addRow(ui_translate(key), widget)
        return layout

    def _repopulate_fields(self, profile: Optional[Profile] = None):
        for key in ('source', 'destination',):
            widget: QComboBox = self._form.__dict__[key]
            current_text = dataclasses.asdict(profile)[key] if profile else widget.currentText()
            widget.clear()
            widget.addItems(dict.fromkeys(relevant_field_names(self._form.note_type.currentText())))
            widget.setCurrentText(current_text)


class FuriganaProfileEditForm(ProfileEditForm, profile_class=ProfileFurigana):
    pass


class PitchProfileEditForm(ProfileEditForm, profile_class=ProfilePitch):

    def _expand_form(self):
        super()._expand_form()
        self._form.output_format = EnumSelectCombo(enum_type=PitchOutputFormat)

    def load_profile(self, profile: ProfilePitch):
        super().load_profile(profile)
        self._form.output_format.setCurrentName(profile.output_format)


class ProfileEdit(QWidget):
    def __init_subclass__(cls, **kwargs):
        cls._profile_class: type(Profile) = kwargs.pop('profile_class')  # suppresses ide warning
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile_list = ProfileList(profile_class=self._profile_class)
        self._edit_form = ProfileEditForm(profile_class=self._profile_class)

        self.setLayout(_main_layout := QHBoxLayout())
        _main_layout.addWidget(self._profile_list)
        _main_layout.addWidget(self._edit_form)
        _main_layout.setContentsMargins(0, 0, 0, 0)

        qconnect(self._profile_list.current_item_changed, self._edit_profile)
        self._profile_list.populate()

    def _edit_profile(self, current: QListWidgetItem, previous: QListWidgetItem):
        self._apply_profile(previous)
        if current:
            self._edit_form.setEnabled(True)
            self._edit_form.load_profile(current.data(Qt.ItemDataRole.UserRole))
        else:
            self._edit_form.setEnabled(False)

    def _apply_profile(self, item: QListWidgetItem):
        if item:
            profile = self._edit_form.as_profile()
            item.setData(Qt.ItemDataRole.UserRole, profile)
            item.setText(profile.name)

    def as_list(self) -> list[dict[str, str]]:
        self._apply_profile(self._profile_list.current_item())
        return [dataclasses.asdict(p) for p in self._profile_list.profiles()]


class FuriganaProfilesEdit(ProfileEdit, profile_class=ProfileFurigana):
    pass


class PitchProfilesEdit(ProfileEdit, profile_class=ProfilePitch):
    pass


class WordsEdit(QTextEdit):
    _min_height = 32
    _font_size = 16

    def __init__(self, initial_values: Optional[list[str]] = None, *args):
        super().__init__(*args)
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
            self.setPlainText(','.join(dict.fromkeys(values)))

    def as_text(self) -> str:
        return ','.join(dict.fromkeys(filter(bool, self.toPlainText().replace(' ', '').split('\n'))))


class SettingsForm(QGroupBox):
    _title = None
    _config = None

    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle(self._title)
        self.setCheckable(False)
        self._widgets = SimpleNamespace()
        self._add_widgets()
        self.setLayout(self._make_layout())

    def _add_widgets(self):
        """Subclasses add new widgets here."""
        self._widgets.__dict__.update(self._create_checkboxes())

    def as_dict(self) -> dict[str, Union[bool, str, int]]:
        return as_config_dict(self._widgets.__dict__)

    def _create_checkboxes(self) -> Iterable[tuple[str, QCheckBox]]:
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


class BehaviorSettingsForm(SettingsForm):
    _title = "Behavior"
    _config = cfg


class ContextMenuSettingsForm(SettingsForm):
    _title = "Context menu"
    _config = cfg.context_menu


class MultiColumnSettingsForm(SettingsForm):
    _columns = 3
    _alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    _widget_min_height = 25
    _column_spacing = 16
    _equal_col_width = False

    def _make_layout(self) -> QLayout:
        layout = QHBoxLayout()
        layout.setSpacing(self._column_spacing)
        for index, chunk in enumerate(split_list(list(self._widgets.__dict__.items()), self._columns)):
            layout.addLayout(form := QFormLayout())
            form.setAlignment(self._alignment)
            for key, widget in chunk:
                widget: QWidget
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                widget.setMinimumHeight(max(widget.minimumHeight(), self._widget_min_height))
                if isinstance(widget, QCheckBox):
                    form.addRow(widget)
                else:
                    form.addRow(ui_translate(key), widget)
            if self._equal_col_width:
                layout.setStretch(index, 1)
        return layout


class NarrowSpinBox(QSpinBox):
    def __init__(self, initial_value: int = None, *args):
        super().__init__(*args)
        self.setRange(1, 99)
        self.setMaximumWidth(NARROW_WIDGET_MAX_WIDTH)
        if initial_value:
            self.setValue(initial_value)


class NarrowLineEdit(QLineEdit):
    def __init__(self, *args):
        super().__init__(*args)
        self.setMaximumWidth(NARROW_WIDGET_MAX_WIDTH)


class PitchSettingsForm(MultiColumnSettingsForm):
    _title = "Pitch Options"
    _config = cfg.pitch_accent

    def _add_widgets(self):
        super()._add_widgets()
        self._widgets.maximum_results = NarrowSpinBox(initial_value=self._config.maximum_results)
        self._widgets.discard_mode = EnumSelectCombo(
            enum_type=ReadingsDiscardMode,
            initial_value=self._config.discard_mode
        )
        self._widgets.reading_separator = NarrowLineEdit(self._config.reading_separator)
        self._widgets.word_separator = NarrowLineEdit(self._config.word_separator)
        self._widgets.lookup_shortcut = ShortCutGrabButton(initial_value=self._config.lookup_shortcut)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)


class FuriganaSettingsForm(MultiColumnSettingsForm):
    _title = "Furigana Options"
    _config = cfg.furigana

    def _add_widgets(self):
        super()._add_widgets()
        self._widgets.maximum_results = NarrowSpinBox(initial_value=self._config.maximum_results)
        self._widgets.discard_mode = EnumSelectCombo(
            enum_type=ReadingsDiscardMode,
            initial_value=self._config.discard_mode
        )
        self._widgets.reading_separator = NarrowLineEdit(self._config.reading_separator)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)
        self._widgets.mecab_only = WordsEdit(initial_values=self._config.mecab_only)


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

    def as_dict(self) -> dict[str, Union[bool, str]]:
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
        for key, button_config in cfg.toolbar.items():
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

    def as_dict(self) -> dict[str, dict[str, Union[str, bool]]]:
        return {
            key: widget.as_dict()
            for key, widget in self._widgets.items()
        }


class SettingsDialog(QDialog):
    name = 'Japanese Options'

    def __init__(self, *args):
        super().__init__(*args)

        # General tab
        self._behavior_settings = BehaviorSettingsForm()
        self._context_menu_settings = ContextMenuSettingsForm()
        self._toolbar_settings = ToolbarSettingsForm()

        # Furigana tab
        self._furigana_profiles_edit = FuriganaProfilesEdit()
        self._furigana_settings = FuriganaSettingsForm()

        # Pitch tab
        self._pitch_profiles_edit = PitchProfilesEdit()
        self._pitch_settings = PitchSettingsForm()

        # Overrides tab
        self._accents_override = PitchOverrideWidget(self, file_path=UserDb.accent_database)

        # Finish layout
        self._tabs = QTabWidget()
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._setup_tabs()
        self._setup_ui()

        # Show window
        restoreGeom(self, self.name, adjustSize=True)
        self.exec()

    def done(self, *args, **kwargs) -> None:
        saveGeom(self, self.name)
        return super().done(*args, **kwargs)

    def _setup_tabs(self):
        # General
        tab = QWidget()
        tab.setLayout(layout := QGridLayout())
        # row, column, rowSpan, columnSpan
        layout.addWidget(self._behavior_settings, 1, 1)
        layout.addWidget(self._context_menu_settings, 2, 1)
        layout.addWidget(self._toolbar_settings, 1, 2, 2, 1)
        for column in (1, 2):
            layout.setColumnStretch(column, 1)
        self._tabs.addTab(tab, "General")

        # Furigana
        tab = QWidget()
        tab.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._furigana_profiles_edit)
        layout.addWidget(self._furigana_settings)
        self._tabs.addTab(tab, "Furigana")

        # Pitch accent
        tab = QWidget()
        tab.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._pitch_profiles_edit)
        layout.addWidget(self._pitch_settings)
        self._tabs.addTab(tab, "Pitch accent")

        # Accent DB override
        self._tabs.addTab(self._accents_override, "Overrides")

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
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
        layout.addWidget(self._tabs)
        layout.addStretch()
        layout.addWidget(self._button_box)
        return layout

    def accept(self) -> None:
        cfg.update(self._behavior_settings.as_dict())
        cfg['pitch_accent'].update(self._pitch_settings.as_dict())
        cfg['furigana'].update(self._furigana_settings.as_dict())
        cfg['context_menu'].update(self._context_menu_settings.as_dict())
        cfg['toolbar'].update(self._toolbar_settings.as_dict())
        cfg['profiles'] = [
            *self._furigana_profiles_edit.as_list(),
            *self._pitch_profiles_edit.as_list()
        ]
        cfg.write_config()
        self._accents_override.save_to_disk()
        acc_dict.reload_from_disk(self)
        return super().accept()


def add_settings_action(root_menu: QMenu):
    menu_action = QAction(f'{SettingsDialog.name}...', root_menu)
    qconnect(menu_action.triggered, lambda: SettingsDialog(mw))
    root_menu.addAction(menu_action)


def add_deck_download_action(root_menu: QMenu):
    menu_action = QAction("Download example deck", root_menu)
    qconnect(menu_action.triggered, lambda: openLink(EXAMPLE_DECK_ANKIWEB_URL))
    root_menu.addAction(menu_action)


def init():
    root_menu = menu_root_entry()
    add_settings_action(root_menu)
    add_deck_download_action(root_menu)
