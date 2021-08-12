from typing import Dict

from aqt import mw
from aqt.qt import *

from .helpers import config, write_config


def make_checkboxes() -> Dict[str, QCheckBox]:
    keys = (
        "regenerate_readings",
        "use_hiragana",
        "use_mecab",
        "generate_on_flush",
        "kana_lookups",
    )
    return {key: QCheckBox(key.capitalize().replace('_', ' ')) for key in keys}


class SettingsDialog(QDialog):
    NAME = "Pitch Accent Options..."

    def __init__(self, parent, *args, **kwargs):
        super(SettingsDialog, self).__init__(parent=parent or mw, *args, **kwargs)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(self.NAME[:-3])
        self.setMinimumSize(420, 240)
        self.checkboxes = make_checkboxes()
        self.setLayout(self.create_main_layout())
        self.load_config_values()

    def create_main_layout(self) -> QLayout:
        main = QVBoxLayout()
        main.addLayout(self.create_checkboxes_layout())
        main.addStretch()
        main.addLayout(self.create_bottom_layout())
        return main

    def create_checkboxes_layout(self) -> QLayout:
        layout = QVBoxLayout()
        for checkbox in self.checkboxes.values():
            layout.addWidget(checkbox)
        return layout

    def create_bottom_layout(self) -> QLayout:
        buttons = (
            ('Ok', self.accept),
            ('Cancel', self.reject)
        )
        hbox = QHBoxLayout()
        for label, action in buttons:
            button = QPushButton(label)
            qconnect(button.clicked, action)
            hbox.addWidget(button)
        hbox.addStretch()
        return hbox

    def load_config_values(self):
        for key, checkbox in self.checkboxes.items():
            checkbox.setChecked(config[key])

    def accept(self) -> None:
        for key, checkbox in self.checkboxes.items():
            config[key] = checkbox.isChecked()
        write_config()
        super(SettingsDialog, self).accept()


def create_options_action(parent: QWidget) -> QAction:
    def open_options():
        dialog = SettingsDialog(mw)
        return dialog.exec_()

    action = QAction(SettingsDialog.NAME, parent)
    qconnect(action.triggered, open_options)
    return action
