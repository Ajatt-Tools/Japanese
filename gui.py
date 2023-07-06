# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import dataclasses
from types import SimpleNamespace
from typing import Optional, Iterable, Collection, TypedDict

from aqt import mw
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom, openLink

from .ajt_common.about_menu import tweak_window, menu_root_entry
from .ajt_common.checkable_combobox import CheckableComboBox
from .ajt_common.consts import ADDON_SERIES
from .ajt_common.grab_key import ShortCutGrabButton
from .audio import aud_src_mgr
from .config_view import config_view as cfg, ReadingsDiscardMode, PitchPatternStyle
from .helpers import ui_translate, split_list
from .helpers.profiles import Profile, ProfileFurigana, ProfilePitch, PitchOutputFormat, ProfileAudio, TaskCaller
from .pitch_accents.user_accents import UserAccentData
from .reading import acc_dict
from .widgets.anki_style import fix_default_anki_style
from .widgets.audio_sources import AudioSourcesTable
from .widgets.enum_selector import EnumSelectCombo
from .widgets.pitch_override_widget import PitchOverrideWidget

EDIT_MIN_WIDTH = 100
NARROW_WIDGET_MAX_WIDTH = 64
EXAMPLE_DECK_ANKIWEB_URL = "https://ankiweb.net/shared/info/1557722832"
ADDON_SETUP_GUIDE = "https://tatsumoto-ren.github.io/blog/anki-japanese-support.html"


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
        if isinstance(widget, TriggeredBySelector):
            d[key] = widget.comma_separated_callers()
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
        return ','.join(caller.name for caller in self.checkedData())


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
        self.setEnabled(False)
        self._profile_class = profile_class
        self.setTitle("Edit Profile")
        self.setCheckable(False)
        self._form = SimpleNamespace(
            name=QLineEdit(),
            note_type=NoteTypeSelector(),
            source=EditableSelector(),
            destination=EditableSelector(),
            triggered_by=TriggeredBySelector(),
            split_morphemes=QCheckBox(),
            overwrite_destination=QCheckBox(),
        )
        self._expand_form()
        self._last_used_profile: Optional[Profile] = None
        self.setLayout(self._make_layout())
        adjust_to_contents(self)
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        qconnect(self._form.note_type.currentIndexChanged, lambda index: self._repopulate_fields())
        self._add_tooltips()

    def _expand_form(self):
        """Subclasses add new widgets here."""
        pass

    def _add_tooltips(self):
        """Subclasses add new tooltips here."""
        self._form.note_type.setToolTip(
            "Profile will be triggered for Note Type names that contain this string.\n"
            "Note Type name matching is case-insensitive."
        )
        self._form.source.setToolTip(
            "Name of the field to get data from, i.e. the raw expression."
        )
        self._form.destination.setToolTip(
            "Name of the field to place generated data to."
        )
        self._form.triggered_by.setToolTip(
            "Names of Anki actions that can trigger this profile's task."
        )
        self._form.split_morphemes.setToolTip(
            "If the source field contains multiple words, try to identify and parse each word.\n"
            "Recommended to disable for vocabulary fields."
        )
        self._form.overwrite_destination.setToolTip(
            "When triggered, always replace existing data in the destination field."
        )

    def as_profile(self) -> Profile:
        return Profile(**self._as_dict())

    def load_profile(self, profile: Profile):
        self._last_used_profile = profile
        self._form.name.setText(profile.name)
        self._form.note_type.repopulate(profile.note_type)
        self._form.split_morphemes.setChecked(profile.split_morphemes)
        self._form.triggered_by.set_enabled_callers(profile.enabled_callers())
        self._form.overwrite_destination.setChecked(profile.overwrite_destination)
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


class AudioProfileEditForm(ProfileEditForm, profile_class=ProfileAudio):
    pass


class ProfileEdit(QWidget):
    def __init_subclass__(cls, **kwargs):
        cls._profile_class: type(Profile) = kwargs.pop('profile_class')  # suppresses ide warning
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile_list = ProfileList(profile_class=self._profile_class)
        self._edit_form = ProfileEditForm(profile_class=self._profile_class)
        self.setLayout(self._create_layout())
        qconnect(self._profile_list.current_item_changed, self._edit_profile)
        self._profile_list.populate()

    def _create_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self._profile_list)
        layout.addWidget(self._edit_form)
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

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


class AudioProfilesEdit(ProfileEdit, profile_class=ProfileAudio):
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
        self._add_tooltips()
        self.setLayout(self._make_layout())

    def _add_widgets(self):
        """Subclasses add new widgets here."""
        self._widgets.__dict__.update(self._create_checkboxes())

    def _add_tooltips(self):
        """Subclasses add new tooltips here."""
        pass

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


class ContextMenuSettingsForm(SettingsForm):
    _title = "Context menu"
    _config = cfg.context_menu

    def _add_tooltips(self):
        super()._add_tooltips()
        for action in self._widgets.__dict__.values():
            action.setToolTip("Show this action in the context menu.")


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
    _default_allowed_range = (1, 99)

    def __init__(self, initial_value: int = None, *args):
        super().__init__(*args)
        self.setRange(*self._default_allowed_range)
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
        self._widgets.style = EnumSelectCombo(
            enum_type=PitchPatternStyle,
            initial_value=self._config.style
        )
        self._widgets.reading_separator = NarrowLineEdit(self._config.reading_separator)
        self._widgets.word_separator = NarrowLineEdit(self._config.word_separator)
        self._widgets.lookup_shortcut = ShortCutGrabButton(initial_value=self._config.lookup_shortcut)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)

    def _add_tooltips(self):
        super()._add_tooltips()
        self._widgets.output_hiragana.setToolTip(
            "Print pitch accents using hiragana.\n"
            "Normally katakana is used to print pitch accent."
        )
        self._widgets.kana_lookups.setToolTip(
            "Attempt to look up a word using its kana reading\n"
            "if there's no entry for its kanji form."
        )
        self._widgets.skip_numbers.setToolTip(
            "Don't add pitch accents to numbers."
        )
        self._widgets.reading_separator.setToolTip(
            "String used to separate multiple accents of a word."
        )
        self._widgets.word_separator.setToolTip(
            "String used to separate multiple words."
        )
        self._widgets.blocklisted_words.setToolTip(
            "A comma-separated list of words that won't be looked up."
        )
        self._widgets.maximum_results.setToolTip(
            "Maximum number of results to output.\n"
            "Too many results are not informative and will bloat Anki cards."
        )
        self._widgets.discard_mode.setToolTip(
            "Approach used when the number of results exceeds the maximum number of results.\n"
            "Keep first — Output only the first accent.\n"
            "Discard extra — Output the first few accents, no more than the maximum number.\n"
            "Discard all — Output nothing."
        )
        self._widgets.lookup_shortcut.setToolTip(
            "A keyboard shortcut for looking up selected text."
        )
        self._widgets.style.setToolTip(
            "Style of pitch accent patterns.\n"
            "If set to \"none\", you can configure your own styles\n"
            "in the Styling section of your card type using CSS class names."
        )


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

    def _add_tooltips(self):
        super()._add_tooltips()
        self._widgets.skip_numbers.setToolTip(
            "Don't add furigana to numbers."
        )
        self._widgets.prefer_literal_pronunciation.setToolTip(
            "Print furigana in a way that shows a word's literal pronunciation."
        )
        self._widgets.reading_separator.setToolTip(
            "String used to separate multiple readings of a word.\n\n"
            "Note that to show more than one reading over a word\n"
            "you need to import a compatible Note Type,\n"
            "like the one provided by Ajatt-Tools."
        )
        self._widgets.blocklisted_words.setToolTip(
            "A comma-separated list of words that won't be looked up.\n"
            "Furigana won't be added."
        )
        self._widgets.mecab_only.setToolTip(
            "A comma-separted list of words that won't be looked up in the bundled dictionary.\n"
            "However, they will still be looked up using Mecab."
        )
        self._widgets.maximum_results.setToolTip(
            "Maximum number of results to output.\n"
            "Too many results are not informative and will bloat Anki cards."
        )
        self._widgets.discard_mode.setToolTip(
            "Approach used when the number of results exceeds the maximum number of results.\n"
            "Keep first — Output only the first accent.\n"
            "Discard extra — Output the first few accents, no more than the maximum number.\n"
            "Discard all — Output nothing."
        )


class AudioSettingsForm(MultiColumnSettingsForm):
    _title = "Audio settings"
    _config = cfg.audio_settings

    def _add_widgets(self):
        super()._add_widgets()
        self._widgets.dictionary_download_timeout = NarrowSpinBox(
            initial_value=self._config.dictionary_download_timeout
        )
        self._widgets.audio_download_timeout = NarrowSpinBox(
            initial_value=self._config.audio_download_timeout
        )
        self._widgets.attempts = NarrowSpinBox(
            initial_value=self._config.attempts
        )
        self._widgets.maximum_results = NarrowSpinBox(
            initial_value=self._config.maximum_results
        )

    def _add_tooltips(self):
        super()._add_tooltips()
        self._widgets.dictionary_download_timeout.setToolTip(
            "Download timeout in seconds."
        )
        self._widgets.audio_download_timeout.setToolTip(
            "Download timeout in seconds."
        )
        self._widgets.attempts.setToolTip(
            "Number of attempts before giving up.\n"
            "Applies to both dictionary downloads and audio downloads."
        )
        self._widgets.ignore_inflections.setToolTip(
            "If enabled, audio recordings of inflected readings won't be added."
        )
        self._widgets.stop_if_one_source_has_results.setToolTip(
            "If enabled, stop searching after audio files were found in at least one source.\n"
            "The order of sources in the table matters."
        )
        self._widgets.maximum_results.setToolTip(
            "Maximum number of audio files to add.\n\n"
            "Note: If a word has several pitch accents,\n"
            "this setting may result in some of them not being represented."
        )


class ToolbarButtonConfig(TypedDict):
    enabled: bool
    shortcut: str
    text: str


class ToolbarButtonSettingsForm(QGroupBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setCheckable(True)
        self._shortcut_edit = ShortCutGrabButton()
        self._label_edit = QLineEdit()
        self.setLayout(self._make_layout())

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        layout.addRow("Shortcut", self._shortcut_edit)
        layout.addRow("Label", self._label_edit)
        return layout

    def setButtonLabel(self, label: str):
        return self._label_edit.setText(label)

    def setButtonKeyboardShortcut(self, shortcut: str):
        return self._shortcut_edit.setValue(shortcut)

    def as_dict(self) -> ToolbarButtonConfig:
        return {
            "enabled": self.isChecked(),
            "shortcut": self._shortcut_edit.value(),
            "text": self._label_edit.text(),
        }


class ToolbarSettingsForm(QGroupBox):
    """
    This form lists settings of each Browser Toolbar button.
    The user can enable or disable a button,
    change its label and keyboard shortcut.
    """

    _columns = 2

    def __init__(self, *args):
        super().__init__(*args)
        self.setTitle("Toolbar")
        self.setCheckable(False)
        self._widgets = {}
        self._create_widgets()
        self.setLayout(self._make_layout())

    def _create_widgets(self):
        for key, button_config in cfg.toolbar.items():
            widget = ToolbarButtonSettingsForm()
            widget.setTitle(ui_translate(key))
            widget.setChecked(button_config.enabled)
            widget.setButtonKeyboardShortcut(button_config.shortcut)
            widget.setButtonLabel(button_config.text)
            self._widgets[key] = widget

    def _make_layout(self) -> QLayout:
        layout = QGridLayout()
        for row_n, chunk in enumerate(split_list(list(self._widgets.values()), self._columns)):
            for col_n, widget in enumerate(chunk):
                # row: int, column: int, rowSpan: int, columnSpan: int
                layout.addWidget(widget, row_n + 1, col_n + 1)
        return layout

    def as_dict(self) -> dict[str, ToolbarButtonConfig]:
        return {
            key: widget.as_dict()
            for key, widget in self._widgets.items()
        }


class AudioSourcesGroup(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Audio sources")
        self.setCheckable(False)
        self._audio_sources_table = AudioSourcesTable().populate(cfg.iter_audio_sources())
        self._bottom_label = QLabel()
        self.setLayout(self._make_layout())
        self._populate()

    def _make_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)  # left, top, right, and bottom
        layout.setSpacing(8)
        layout.addWidget(self._audio_sources_table)
        layout.addWidget(self._bottom_label)
        fix_default_anki_style(self._audio_sources_table)
        return layout

    def _populate(self):
        audio_stats = aud_src_mgr.total_stats()
        self._bottom_label.setText(
            f"<strong>Unique files</strong>: {audio_stats.unique_files}. "
            f"<strong>Unique headwords</strong>: {audio_stats.unique_headwords}."
        )

    def iterateConfigs(self):
        return self._audio_sources_table.iterateConfigs()


class SettingsDialog(QDialog):
    name = 'Japanese Options'

    def __init__(self, *args):
        super().__init__(*args)

        # General tab
        self._context_menu_settings = ContextMenuSettingsForm()
        self._toolbar_settings = ToolbarSettingsForm()

        # Furigana tab
        self._furigana_profiles_edit = FuriganaProfilesEdit()
        self._furigana_settings = FuriganaSettingsForm()

        # Pitch tab
        self._pitch_profiles_edit = PitchProfilesEdit()
        self._pitch_settings = PitchSettingsForm()

        # Audio tab
        self._audio_profiles_edit = AudioProfilesEdit()
        self._audio_sources_edit = AudioSourcesGroup()
        self._audio_settings = AudioSettingsForm()

        # Overrides tab
        self._accents_override = PitchOverrideWidget(self, file_path=UserAccentData.source_csv_path)

        # Finish layout
        self._tabs = QTabWidget()
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Help
        )
        self._setup_tabs()
        self._add_tooltips()
        self._setup_ui()

        # Show window
        restoreGeom(self, self.name, adjustSize=True)
        self.exec()

    def done(self, *args, **kwargs) -> None:
        saveGeom(self, self.name)
        return super().done(*args, **kwargs)

    def _setup_tabs(self):
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

        # Audio
        tab = QWidget()
        tab.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._audio_profiles_edit)
        layout.addWidget(self._audio_sources_edit)
        layout.addWidget(self._audio_settings)
        self._tabs.addTab(tab, "Audio")

        # Accent DB override
        self._tabs.addTab(self._accents_override, "Overrides")

        # Menus
        tab = QWidget()
        tab.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._toolbar_settings)
        layout.addWidget(self._context_menu_settings)
        self._tabs.addTab(tab, "Menus")

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle(f'{ADDON_SERIES} {self.name}')
        self.setMinimumSize(800, 600)
        tweak_window(self)
        self.setLayout(self.make_layout())
        self.connect_widgets()

    def _add_tooltips(self):
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setToolTip(
            "Save settings and close the dialog."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Discard settings and close the dialog."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Help).setToolTip(
            "Open Guide."
        )

    def connect_widgets(self):
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)
        qconnect(self._button_box.helpRequested, lambda: openLink(ADDON_SETUP_GUIDE))

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addWidget(self._tabs)
        layout.addStretch()
        layout.addWidget(self._button_box)
        return layout

    def accept(self) -> None:
        cfg['pitch_accent'].update(self._pitch_settings.as_dict())
        cfg['furigana'].update(self._furigana_settings.as_dict())
        cfg['context_menu'].update(self._context_menu_settings.as_dict())
        cfg['toolbar'].update(self._toolbar_settings.as_dict())
        cfg['profiles'] = [
            *self._furigana_profiles_edit.as_list(),
            *self._pitch_profiles_edit.as_list(),
            *self._audio_profiles_edit.as_list(),
        ]
        cfg['audio_sources'] = [
            dataclasses.asdict(source)
            for source in self._audio_sources_edit.iterateConfigs()
        ]
        cfg['audio_settings'].update(self._audio_settings.as_dict())
        # Write the new data to disk
        cfg.write_config()
        self._accents_override.save_to_disk()
        # Reload
        acc_dict.reload_from_disk()
        aud_src_mgr.init_audio_dictionaries(notify_on_finish=True)
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
