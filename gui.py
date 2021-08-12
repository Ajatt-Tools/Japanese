from aqt import mw
from aqt.qt import *


class SettingsDialog(QDialog):
    NAME = "Pitch Accent Options..."

    def __init__(self, parent, *args, **kwargs):
        super(SettingsDialog, self).__init__(parent=parent or mw, *args, **kwargs)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(self.NAME[:-3])
        self.setMinimumSize(420, 240)
        self.setLayout(self.create_main_layout())

    def create_main_layout(self) -> QLayout:
        main = QVBoxLayout()
        main.addStretch()
        main.addLayout(self.create_bottom_layout())
        return main

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


def create_options_action(parent: QWidget) -> QAction:
    def open_options():
        dialog = SettingsDialog(mw)
        return dialog.exec_()

    action = QAction(SettingsDialog.NAME, parent)
    qconnect(action.triggered, open_options)
    return action
