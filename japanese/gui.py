# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Optional, TypedDict, cast, final

from aqt import mw
from aqt.addons import AddonsDialog, ConfigEditor
from aqt.operations import QueryOp
from aqt.qt import *
from aqt.utils import openLink, tooltip

from .ajt_common.about_menu import menu_root_entry, tweak_window
from .ajt_common.addon_config import (
    MgrPropMixIn,
    set_config_action,
    set_config_update_action,
)
from .ajt_common.anki_field_selector import EditableSelector
from .ajt_common.enum_select_combo import EnumSelectCombo
from .ajt_common.grab_key import ShortCutGrabButton
from .ajt_common.model_utils import relevant_field_names
from .ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from .ajt_common.utils import ui_translate
from .audio import aud_src_mgr, show_audio_init_result_tooltip
from .audio_manager.basic_types import (
    AudioSourceConfig,
    NameUrl,
    NameUrlSet,
    TotalAudioStats,
)
from .audio_manager.source_manager import InitResult
from .config_view import config_view as cfg
from .helpers.consts import ADDON_NAME, THIS_ADDON_MODULE
from .helpers.misc import split_list
from .helpers.profiles import (
    ColorCodePitchFormat,
    PitchOutputFormat,
    Profile,
    ProfileAudio,
    ProfileFurigana,
    ProfilePitch,
    TaskCaller,
)
from .note_type.note_type import prepare_note_types
from .pitch_accents.consts import USER_DATA_CSV_PATH
from .reading import acc_dict
from .widgets.anki_style import fix_default_anki_style
from .widgets.audio_sources import AudioSourcesTable, tooltip_cache_remove_complete
from .widgets.audio_sources_stats import AudioStatsDialog
from .widgets.enum_selector import FlagSelectCombo
from .widgets.pitch_override_widget import PitchOverrideWidget
from .widgets.settings_form import (
    AudioSettingsForm,
    ContextMenuSettingsForm,
    ForvoSettingsForm,
    FuriganaSettingsForm,
    PitchSettingsForm,
    SettingsForm,
)
from .widgets.svg_settings import SvgSettingsWidget
from .widgets.widgets_to_config_dict import as_config_dict

EDIT_MIN_WIDTH = 100
EXAMPLE_DECK_ANKIWEB_URL = "https://ankiweb.net/shared/info/1557722832"
ADDON_SETUP_GUIDE = "https://tatsumoto-ren.github.io/blog/anki-japanese-support.html"


def adjust_to_contents(widget: QWidget) -> None:
    try:
        widget.setSizeAdjustPolicy(widget.AdjustToContents)
    except AttributeError:
        pass


def is_obj_deleted(self: QWidget) -> bool:
    try:
        self.isVisible()
    except RuntimeError:
        return True
    else:
        return False


class ControlPanel(QHBoxLayout):
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.clone_btn = QPushButton("Clone")
        self.addWidget(self.add_btn)
        self.addWidget(self.remove_btn)
        self.addWidget(self.clone_btn)


class NoteTypeSelector(EditableSelector):
    def repopulate(self, current_text: Optional[str]) -> None:
        self.clear()
        self.addItems([n.name for n in mw.col.models.all_names_and_ids()])
        if current_text:
            self.setCurrentText(current_text)
        elif self.count() > 0:
            self.setCurrentIndex(0)


class ProfileList(QGroupBox):
    def __init__(self, profile_class: type[Profile], *args) -> None:
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

    def current_item(self) -> Optional[QListWidgetItem]:
        return self._list_widget.currentItem()

    def profiles(self) -> Iterable[Profile]:
        for idx in range(self._list_widget.count()):
            yield self._list_widget.item(idx).data(Qt.ItemDataRole.UserRole)

    def _setup_signals(self) -> None:
        self.current_item_changed = self._list_widget.currentItemChanged
        qconnect(self._control_panel.add_btn.clicked, self.add_profile)
        qconnect(self._control_panel.remove_btn.clicked, self.remove_current)
        qconnect(self._control_panel.clone_btn.clicked, self.clone_profile)

    def add_profile(self) -> None:
        self.add_and_select(self._store_type.new())

    def remove_current(self) -> Optional[int]:
        if (current := self.current_item()) and current.isSelected():
            self._list_widget.takeItem(row := self._list_widget.currentRow())
            return row
        return None

    def clone_profile(self) -> None:
        if (current := self.current_item()) and current.isSelected():
            self.add_and_select(Profile.clone(current.data(Qt.ItemDataRole.UserRole)))

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addWidget(self._list_widget)
        layout.addLayout(self._control_panel)
        return layout

    def populate(self) -> None:
        self._list_widget.clear()
        for profile in cfg.iter_profiles():
            if isinstance(profile, self._store_type):
                self.add_and_select(profile)
        self._list_widget.setCurrentRow(0)

    def add_and_select(self, profile: Profile) -> None:
        count = self._list_widget.count()
        item = QListWidgetItem()
        item.setText(profile.name)
        item.setData(Qt.ItemDataRole.UserRole, profile)
        self._list_widget.addItem(item)
        self._list_widget.setCurrentRow(count)


class ProfileEditForm(QGroupBox):
    # e.g. ProfileFurigana => FuriganaProfileEditForm
    _subclasses_map: dict[type[Profile], type["ProfileEditForm"]] = {}
    _last_used_profile: Optional[Profile]

    def __init_subclass__(cls, **kwargs) -> None:
        profile_class: type[Profile] = kwargs.pop("profile_class")  # suppresses ide warning
        super().__init_subclass__(**kwargs)
        cls._subclasses_map[profile_class] = cls

    def __new__(cls, profile_class: type[Profile], *args, **kwargs) -> None:
        subclass = cls._subclasses_map[profile_class]
        return QGroupBox.__new__(subclass)

    def __init__(self, profile_class: type[Profile], *args) -> None:
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
            triggered_by=FlagSelectCombo(enum_type=TaskCaller),
            split_morphemes=QCheckBox(),
            overwrite_destination=QCheckBox(),
        )
        self._expand_form()
        self._last_used_profile = None
        self.setLayout(self._make_layout())
        adjust_to_contents(self)
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        qconnect(self._form.note_type.currentIndexChanged, lambda index: self._repopulate_fields())
        self._add_tooltips()

    def _expand_form(self) -> None:
        """Subclasses add new widgets here."""
        pass

    def _add_tooltips(self) -> None:
        """Subclasses add new tooltips here."""
        self._form.note_type.setToolTip(
            "Profile will be triggered for Note Type names that contain this string.\n"
            "Note Type name matching is case-insensitive."
        )
        self._form.source.setToolTip("Name of the field to get data from, i.e. the raw expression.")
        self._form.destination.setToolTip("Name of the field to place generated data to.")
        self._form.triggered_by.setToolTip("Names of Anki actions that can trigger this profile's task.")
        self._form.split_morphemes.setToolTip(
            "If the source field contains multiple words, try to identify and parse each word.\n"
            "Recommended to disable for vocabulary fields."
        )
        self._form.overwrite_destination.setToolTip(
            "When triggered, always replace existing data in the destination field."
        )

    def as_profile(self) -> Profile:
        return Profile.from_config_dict(self._as_dict())

    def load_profile(self, profile: Profile) -> None:
        self._last_used_profile = profile
        self._form.name.setText(profile.name)
        self._form.note_type.repopulate(profile.note_type)
        self._form.split_morphemes.setChecked(profile.split_morphemes)
        self._form.triggered_by.set_checked_flags(profile.triggered_by)
        self._form.overwrite_destination.setChecked(profile.overwrite_destination)
        self._repopulate_fields(profile)

    def _as_dict(self) -> dict[str, Union[str, bool]]:
        return self._last_used_profile.as_config_dict() | as_config_dict(self._form.__dict__)

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        for key, widget in self._form.__dict__.items():
            layout.addRow(ui_translate(key), widget)
        return layout

    def _repopulate_fields(self, profile: Optional[Profile] = None) -> None:
        for key in ("source", "destination"):
            widget: QComboBox = self._form.__dict__[key]
            current_text = profile.as_config_dict()[key] if profile else widget.currentText()
            widget.clear()
            widget.addItems(dict.fromkeys(relevant_field_names(self._form.note_type.currentText().strip())))
            widget.setCurrentText(current_text)


class FuriganaProfileEditForm(ProfileEditForm, profile_class=ProfileFurigana):
    def _expand_form(self) -> None:
        super()._expand_form()
        self._form.color_code_pitch = FlagSelectCombo(enum_type=ColorCodePitchFormat)

    def load_profile(self, profile: ProfileFurigana) -> None:
        super().load_profile(profile)
        self._form.color_code_pitch.set_checked_flags(profile.color_code_pitch)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._form.color_code_pitch.setToolTip(
            "One or more variants to color-code pitch accents in words or sentences."
        )


class PitchProfileEditForm(ProfileEditForm, profile_class=ProfilePitch):
    def _expand_form(self) -> None:
        super()._expand_form()
        self._form.output_format = EnumSelectCombo(enum_type=PitchOutputFormat)

    def load_profile(self, profile: ProfilePitch) -> None:
        super().load_profile(profile)
        self._form.output_format.setCurrentName(profile.output_format)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._form.output_format.setToolTip(
            "Format of the pitch accent information written to Destination.\n"
            "SVG will output an SVG image. Other options output HTML code."
        )


class AudioProfileEditForm(ProfileEditForm, profile_class=ProfileAudio):
    pass


class ProfileEdit(QWidget):
    _profile_class: type[Profile]

    def __init_subclass__(cls, **kwargs) -> None:
        cls._profile_class = kwargs.pop("profile_class")  # suppresses ide warning
        super().__init_subclass__(**kwargs)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._profile_list = ProfileList(profile_class=self._profile_class)
        self._edit_form = ProfileEditForm(profile_class=self._profile_class)
        self.setLayout(self._create_layout())
        qconnect(self._profile_list.current_item_changed, self._edit_profile)
        self._profile_list.populate()

    def _create_layout(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(self._profile_list)
        layout.addWidget(self._edit_form)
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def _edit_profile(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        self._apply_profile(previous)
        if current:
            self._edit_form.setEnabled(True)
            self._edit_form.load_profile(current.data(Qt.ItemDataRole.UserRole))
        else:
            self._edit_form.setEnabled(False)

    def _apply_profile(self, item: Optional[QListWidgetItem]) -> None:
        if item:
            profile = self._edit_form.as_profile()
            item.setData(Qt.ItemDataRole.UserRole, profile)
            item.setText(profile.name)

    def as_list(self) -> list[dict[str, str]]:
        self._apply_profile(self._profile_list.current_item())
        return [p.as_config_dict() for p in self._profile_list.profiles()]


class FuriganaProfilesEdit(ProfileEdit, profile_class=ProfileFurigana):
    pass


class PitchProfilesEdit(ProfileEdit, profile_class=ProfilePitch):
    pass


class AudioProfilesEdit(ProfileEdit, profile_class=ProfileAudio):
    pass


class GroupBoxWrapper(QGroupBox):
    def __init__(self, settings_form: SettingsForm, *args) -> None:
        super().__init__(*args)
        self._form = settings_form
        self.setTitle(settings_form.title)
        self.setCheckable(False)
        self.setLayout(settings_form.layout())

    def as_dict(self) -> dict[str, Union[bool, str, int]]:
        return self._form.as_dict()


class ToolbarButtonConfig(TypedDict):
    enabled: bool
    shortcut: str
    text: str


class ToolbarButtonSettingsForm(QGroupBox):
    def __init__(self, *args) -> None:
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

    def setButtonLabel(self, label: str) -> None:
        return self._label_edit.setText(label)

    def setButtonKeyboardShortcut(self, shortcut: str) -> None:
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

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setTitle("Toolbar")
        self.setCheckable(False)
        self._widgets = {}
        self._create_widgets()
        self.setLayout(self._make_layout())

    def _create_widgets(self) -> None:
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
        return {key: widget.as_dict() for key, widget in self._widgets.items()}


class AudioSourcesEditTable(QWidget):
    """
    A table that shows imported audio sources.
    The stats are shown at the bottom.
    """

    _audio_stats: Optional[TotalAudioStats]
    _filename_filter: str = "JSON Files (*.json);; All Files (*.*)"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._audio_sources_table = AudioSourcesTable().populate(cfg.iter_audio_sources())
        self._bottom_label = QLabel()
        self._audio_stats = None
        self._apply_button = QPushButton("Apply")
        self._stats_button = QPushButton("Statistics")
        self._purge_button = QPushButton("Purge database")
        self._choose_file_button = QPushButton("Choose file")
        self.setLayout(self._make_layout())
        self._populate()
        self._connect_widgets()
        self._add_tooltips()

    def _make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 0, 4, 0)  # left, top, right, and bottom
        layout.setSpacing(8)
        layout.addWidget(self._audio_sources_table)
        layout.addLayout(self._make_bottom_layout())
        fix_default_anki_style(self._audio_sources_table)
        return layout

    def _make_bottom_layout(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(self._apply_button)
        layout.addWidget(self._bottom_label)
        layout.addStretch(1)
        layout.addWidget(self._choose_file_button)
        layout.addWidget(self._stats_button)
        layout.addWidget(self._purge_button)
        return layout

    def _connect_widgets(self) -> None:
        qconnect(self._purge_button.clicked, self._on_purge_db_clicked)
        qconnect(self._stats_button.clicked, self._on_show_statistics_clicked)
        qconnect(self._apply_button.clicked, self._on_apply_clicked)
        qconnect(self._choose_file_button.clicked, self._on_choose_file_clicked)
        qconnect(self._audio_sources_table.remove_requested, self._on_remove_selected_sources_clicked)

    def _populate(self) -> None:
        assert mw
        QueryOp(
            parent=mw,
            op=lambda collection: aud_src_mgr.get_statistics(),
            success=lambda audio_stats: self._remember_and_update_stats(audio_stats),
        ).without_collection().run_in_background()

    def _remember_and_update_stats(self, audio_stats: TotalAudioStats) -> None:
        if is_obj_deleted(self):
            return
        self._audio_stats = audio_stats
        self._bottom_label.setText(
            f"<strong>Unique files</strong>: {audio_stats.unique_files}. "
            f"<strong>Unique headwords</strong>: {audio_stats.unique_headwords}."
        )

    def _on_show_statistics_clicked(self) -> None:
        if not self._audio_stats:
            return
        AudioStatsDialog().load_data(self._audio_stats).exec()

    def _on_purge_db_clicked(self) -> None:
        aud_src_mgr.purge_everything(on_finish=self._populate)

    def _on_apply_clicked(self) -> None:
        self._apply_button.setEnabled(False)
        cfg["audio_sources"] = [source.as_config_dict() for source in self.iterateConfigs()]
        cfg.write_config()
        aud_src_mgr.init_sources_anki(on_finish=self._on_audio_sources_init_finished)

    def _on_audio_sources_init_finished(self, result: InitResult) -> None:
        self._apply_button.setEnabled(True)
        if result.did_run:
            self._populate()

    def _on_remove_selected_sources_clicked(self, selected_sources: NameUrlSet) -> None:
        """
        Remove cached rows for the selected audio sources.
        Missing audio sources are skipped.
        """
        self._apply_button.setEnabled(False)
        aud_src_mgr.remove_sources_from_db(selected_sources, on_finish=self._on_remove_selected_sources_finished)

    def _on_remove_selected_sources_finished(self, removed: list[NameUrl]) -> None:
        self._apply_button.setEnabled(True)
        if removed:
            self._populate()
        tooltip_cache_remove_complete(removed)

    def _on_choose_file_clicked(self) -> None:
        name, mime = QFileDialog.getOpenFileName(
            parent=cast(QWidget, self),
            caption="Load audio source from JSON File",
            directory=cfg["last_file_save_location"],
            filter=self._filename_filter,
        )
        if not name:
            return tooltip("Aborted.", parent=self)
        self._audio_sources_table.addSource(AudioSourceConfig(True, os.path.splitext(os.path.basename(name))[0], name))
        cfg["last_file_save_location"] = name  # may or may not be lost

    def iterateConfigs(self) -> Iterable[AudioSourceConfig]:
        return self._audio_sources_table.iterateConfigs()

    def _add_tooltips(self) -> None:
        self._stats_button.setToolTip("Show statistics for each imported audio source.")
        self._purge_button.setToolTip("Remove the database file.\nIt will be recreated from scratch again.")
        self._apply_button.setToolTip("Apply current sources configuration.")


@final
class SettingsDialog(AnkiSaveAndRestoreGeomDialog, MgrPropMixIn):
    name: str = "ajt__japanese_options"

    def __init__(self, *args) -> None:
        super().__init__(*args)

        # Furigana tab
        self._furigana_profiles_edit = FuriganaProfilesEdit()
        self._furigana_settings = GroupBoxWrapper(FuriganaSettingsForm(cfg.furigana))

        # Pitch tab
        self._pitch_profiles_edit = PitchProfilesEdit()
        self._pitch_settings = GroupBoxWrapper(PitchSettingsForm(cfg.pitch_accent))
        self._svg_settings = SvgSettingsWidget(cfg.svg_graphs)

        # Audio tab
        self._audio_profiles_edit = AudioProfilesEdit()
        self._audio_settings = GroupBoxWrapper(AudioSettingsForm(cfg.audio_settings))

        # Audio sources
        self._audio_sources_edit = AudioSourcesEditTable()

        # Menus tab
        self._toolbar_settings = ToolbarSettingsForm()
        self._context_menu_settings = GroupBoxWrapper(ContextMenuSettingsForm(cfg.context_menu))
        self._forvo_settings = GroupBoxWrapper(ForvoSettingsForm(cfg.forvo))

        # Overrides tab
        self._accents_override = PitchOverrideWidget(self, file_path=USER_DATA_CSV_PATH)

        # Finish layout
        self._tabs = QTabWidget()
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Help
        )
        self._setup_tabs()
        self._add_tooltips()
        self._setup_ui()
        self._add_advanced_button()

        # Show window
        self.exec()

    def _setup_tabs(self) -> None:
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

        # SVG settings
        self._tabs.addTab(self._svg_settings, "SVG graphs")

        # Audio
        tab = QWidget()
        tab.setLayout(layout := QVBoxLayout())
        layout.addWidget(self._audio_profiles_edit)
        layout.addWidget(self._audio_settings)
        self._tabs.addTab(tab, "Audio")

        # Audio sources
        self._tabs.addTab(self._audio_sources_edit, "Audio sources")

        # Accent DB override
        self._tabs.addTab(self._accents_override, "Overrides")

        # Menus
        tab = QWidget()
        tab.setLayout(layout := QGridLayout())
        # int fromRow, int fromColumn, int rowSpan, int columnSpan
        layout.addWidget(self._toolbar_settings, 0, 0, 1, -1)
        layout.addWidget(self._context_menu_settings, 1, 0)
        layout.addWidget(self._forvo_settings, 1, 1)
        self._tabs.addTab(tab, "Menus")
        # Note: create equally sized columns.
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def _setup_ui(self) -> None:
        cast(QDialog, self).setWindowModality(Qt.WindowModality.ApplicationModal)
        cast(QDialog, self).setWindowTitle(f"{ADDON_NAME} - Options")
        self.setMinimumSize(800, 600)
        tweak_window(self)
        self.setLayout(self.make_layout())
        self.connect_widgets()

    def _add_tooltips(self) -> None:
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setToolTip("Save settings and close the dialog.")
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Discard settings and close the dialog."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Help).setToolTip("Open Guide.")

    def connect_widgets(self) -> None:
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
        # https://doc.qt.io/qt-6/qdialog.html#accept
        cfg["pitch_accent"].update(self._pitch_settings.as_dict())
        cfg["svg_graphs"].update(self._svg_settings.as_dict())
        cfg["furigana"].update(self._furigana_settings.as_dict())
        cfg["context_menu"].update(self._context_menu_settings.as_dict())
        cfg["forvo"].update(self._forvo_settings.as_dict())
        cfg["toolbar"].update(self._toolbar_settings.as_dict())
        cfg["profiles"] = [
            *self._furigana_profiles_edit.as_list(),
            *self._pitch_profiles_edit.as_list(),
            *self._audio_profiles_edit.as_list(),
        ]
        cfg["audio_sources"] = [source.as_config_dict() for source in self._audio_sources_edit.iterateConfigs()]
        cfg["audio_settings"].update(self._audio_settings.as_dict())
        # Write the new data to disk
        cfg.del_deprecated_keys()
        cfg.write_config()
        self._accents_override.save_to_disk()
        # Reload
        acc_dict.reload_user_accents_from_disk()
        aud_src_mgr.init_sources_anki(on_finish=show_audio_init_result_tooltip)
        # if new profiles were added, add imports to the note types.
        prepare_note_types()
        return super().accept()

    def _add_advanced_button(self) -> None:
        def on_advanced_clicked() -> None:
            d = ConfigEditor(
                dlg=cast(AddonsDialog, self),
                addon=THIS_ADDON_MODULE,
                conf=cfg.dict_copy(),
            )
            qconnect(d.accepted, self.reject)

        b = self._button_box.addButton("Advanced", QDialogButtonBox.ButtonRole.ResetRole)
        qconnect(b.clicked, on_advanced_clicked)


def add_settings_action(root_menu: QMenu) -> None:
    menu_action = QAction("Japanese Options...", root_menu)
    qconnect(menu_action.triggered, lambda: SettingsDialog(mw))
    root_menu.addAction(menu_action)


def add_deck_download_action(root_menu: QMenu) -> None:
    menu_action = QAction("Download example deck", root_menu)
    qconnect(menu_action.triggered, lambda: openLink(EXAMPLE_DECK_ANKIWEB_URL))
    root_menu.addAction(menu_action)


def init() -> None:
    root_menu = menu_root_entry()
    add_settings_action(root_menu)
    add_deck_download_action(root_menu)
    set_config_action(lambda: SettingsDialog(mw))
    set_config_update_action(cfg.update_from_addon_manager)
