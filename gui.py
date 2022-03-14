# Copyright: (C) 2022 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
import dataclasses
from types import SimpleNamespace
from typing import Optional, Iterable, Dict, List, NamedTuple

from aqt import mw
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom

from .ajt_common import menu_root_entry, tweak_window, ShortCutGrabButton, ADDON_SERIES
from .helpers import ui_translate
from .helpers.config import TaskMode, Profile, config, write_config, list_profiles

EDIT_MIN_WIDTH = 100


def adjust_to_contents(widget: QWidget):
    try:
        widget.setSizeAdjustPolicy(widget.AdjustToContents)
    except AttributeError:
        pass


class ControlPanel(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        self.addWidget(self.add_btn)
        self.addWidget(self.remove_btn)


class RowState(NamedTuple):
    previous: Optional[int]
    current: int


class ProfileList(QGroupBox):
    current_row_changed = pyqtSignal(RowState, name="Current row changed")

    def __init__(self):
        super().__init__()
        self.setTitle("Profiles")
        self.setCheckable(False)
        self._row = None
        self._list_widget = QListWidget()
        self._control_panel = ControlPanel()
        self.setMinimumWidth(EDIT_MIN_WIDTH)
        self.setLayout(self.make_layout())
        self._pass_signals()
        adjust_to_contents(self._list_widget)

    @property
    def current_row(self) -> int:
        return self._list_widget.currentRow()

    def _pass_signals(self):
        self.add_clicked = self._control_panel.add_btn.clicked
        self.remove_clicked = self._control_panel.remove_btn.clicked
        qconnect(self._list_widget.currentRowChanged, self.on_current_row_changed)

    def on_current_row_changed(self, current_row: int):
        self.current_row_changed.emit(RowState(previous=self._row, current=current_row))  # type: ignore
        self._row = current_row

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addWidget(self._list_widget)
        layout.addLayout(self._control_panel)
        return layout

    def remove_current(self) -> Optional[int]:
        if (current := self._list_widget.currentItem()) and current.isSelected():
            self._list_widget.takeItem(row := self._list_widget.currentRow())
            return row

    def populate(self, labels: Iterable[str]):
        self._list_widget.clear()
        self._list_widget.addItems(labels)
        self._list_widget.setCurrentRow(0)

    def add_and_select(self, label: str):
        count = self._list_widget.count()
        self._list_widget.addItem(label)
        self._list_widget.setCurrentRow(count)

    def set_text(self, row: int, text: str):
        self._list_widget.item(row).setText(text)

    def set_current_text(self, text: str):
        self._list_widget.currentItem().setText(text)


def relevant_field_names(note_type_name_fuzzy: Optional[str]) -> Iterable[str]:
    """
    Return an iterable of field names present in note types whose names contain the first parameter.
    """
    for tup in mw.col.models.all_names_and_ids():
        if not note_type_name_fuzzy or note_type_name_fuzzy.lower() in tup.name.lower():
            for field in mw.col.models.get(tup.id)['flds']:
                yield field['name']


class EditableSelector(QComboBox):
    def __init__(self):
        super().__init__()
        self.setEditable(True)


class NoteTypeSelector(EditableSelector):
    def repopulate(self, current_profile_name: Optional[str]):
        self.clear()
        self.addItems([n.name for n in mw.col.models.all_names_and_ids()])
        if current_profile_name:
            self.setCurrentText(current_profile_name)
        elif self.count() > 0:
            self.setCurrentIndex(0)


class ModeSelector(QComboBox):
    def __init__(self):
        super().__init__()
        self.addItems(mode.name.capitalize() for mode in TaskMode)

    def setCurrentText(self, text: str):
        return super().setCurrentText(text.capitalize())

    def currentText(self) -> str:
        return super().currentText().lower()


class ProfileEditForm(QGroupBox):
    def __init__(self):
        super().__init__()
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
        return {
            key: widget.currentText() if isinstance(widget, QComboBox) else widget.text()
            for key, widget in self._form.__dict__.items()
        }

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


class PitchSettingsForm(QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle("Pitch Settings")
        self.setCheckable(False)
        self._checkboxes = self.create_checkboxes()
        self._shortcut_edit = ShortCutGrabButton(initial_value=config['lookup_shortcut'])
        self.setLayout(self.make_layout())

    def as_dict(self) -> Dict[str, Union[bool, str]]:
        shortcut = {
            'lookup_shortcut': self._shortcut_edit.value()
        }
        checkboxes = {
            key: widget.isChecked() for key, widget in self._checkboxes.items()
        }
        return shortcut | checkboxes

    @staticmethod
    def create_checkboxes() -> Dict[str, QCheckBox]:
        return {
            key: QCheckBox(ui_translate(key))
            for key, value in config.items()
            if type(value) == bool
        }

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        for key, widget in self._checkboxes.items():
            layout.addWidget(widget)
            widget.setChecked(config[key])
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("Lookup shortcut"))
        shortcut_layout.addWidget(self._shortcut_edit)
        shortcut_layout.addStretch()
        layout.addLayout(shortcut_layout)
        return layout


class SettingsDialog(QDialog):
    name = 'Japanese Options'

    def __init__(self, parent: QWidget):
        QDialog.__init__(self, parent)
        self._profiles: List[Profile] = list_profiles()
        self._left_panel = ProfileList()
        self._right_panel = ProfileEditForm()
        self._pitch_settings = PitchSettingsForm()
        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._setup_ui()
        restoreGeom(self, self.name, adjustSize=True)
        self.exec()
        saveGeom(self, self.name)

    def _setup_ui(self) -> None:
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(f'{ADDON_SERIES} {self.name}')
        self.setMinimumSize(420, 240)
        tweak_window(self)
        self.setLayout(self.make_layout())
        self.populate_ui()
        self.connect_widgets()

    def make_layout(self) -> QLayout:
        layout = QVBoxLayout()
        layout.addLayout(self.make_profiles_form())
        layout.addWidget(self._pitch_settings)
        layout.addStretch()
        layout.addWidget(self._button_box)
        return layout

    def make_profiles_form(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(self._left_panel)
        layout.addWidget(self._right_panel)
        return layout

    def populate_ui(self):
        self._left_panel.populate(item.name for item in self._profiles)
        self.edit_profile(RowState(None, 0))

    def connect_widgets(self):
        qconnect(self._left_panel.add_clicked, self.add_profile)
        qconnect(self._left_panel.remove_clicked, self.remove_profile)
        qconnect(self._left_panel.current_row_changed, self.edit_profile)
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def add_profile(self):
        self._profiles.append(Profile.new())
        self._left_panel.add_and_select(self._profiles[-1].name)

    def remove_profile(self):
        if (row := self._left_panel.remove_current()) is not None:
            del self._profiles[row]

    def edit_profile(self, row: RowState):
        if row.previous is not None:
            self.apply_profile_settings(row.previous)
        if row.current >= 0 and len(self._profiles) > 0:
            self._right_panel.setEnabled(True)
            self._right_panel.load_profile(self._profiles[row.current])
        else:
            self._right_panel.setEnabled(False)

    def apply_profile_settings(self, row: int):
        self._profiles[row] = Profile(**self._right_panel.as_dict())
        self._left_panel.set_text(row, self._profiles[row].name)

    def accept(self) -> None:
        self.apply_profile_settings(self._left_panel.current_row)
        config.update(self._pitch_settings.as_dict())
        config['profiles'] = [dataclasses.asdict(p) for p in self._profiles]
        write_config()
        QDialog.accept(self)


def init():
    root_menu = menu_root_entry()
    menu_action = QAction(f'{SettingsDialog.name}...', root_menu)
    qconnect(menu_action.triggered, lambda: SettingsDialog(mw))
    root_menu.addAction(menu_action)
