# -*- coding: utf-8 -*-
#
# Copyright: (C) 2021 Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#

from typing import Iterable

from aqt import mw
from aqt.qt import *

from .helpers import *


class ItemSelectionDialog(QDialog):
    def __init__(self, items: Iterable, title: str = "Select", parent: QWidget = mw):
        super(ItemSelectionDialog, self).__init__(parent=parent)
        self.setWindowTitle(title)
        self.setMinimumSize(320, 240)
        self.list_widget = self.create_list_widget(items)
        self.setLayout(self.create_root_layout())

    def create_root_layout(self) -> QLayout:
        root_layout = QVBoxLayout()
        root_layout.addWidget(self.list_widget)
        root_layout.addWidget(self.create_button_box())
        return root_layout

    @staticmethod
    def create_list_widget(items: Iterable):
        list_widget = QListWidget()
        list_widget.addItems(items)
        list_widget.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        return list_widget

    def create_button_box(self):
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        button_box.accepted.connect(self.accept_if_selected)
        button_box.rejected.connect(self.reject)
        return button_box

    def accept_if_selected(self) -> None:
        if self.list_widget.currentItem().isSelected() is False:
            self.reject()
        else:
            self.accept()

    def selected_text(self):
        return self.list_widget.currentItem().text()


class ListEdit(QWidget):
    def __init__(
            self,
            parent: QWidget,
            items: Iterable[str],
            available_items: Iterable[str],
            available_items_title: str
    ):
        super(ListEdit, self).__init__(parent)
        self.parent = parent
        self.available_items = available_items
        self.available_items_title = available_items_title
        self.list_widget = self.create_list_widget(items)
        self.setLayout(self.create_root_layout())

    def create_list_widget(self, items: Iterable):
        list_widget = QListWidget()
        list_widget.addItems(items)
        list_widget.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        qconnect(list_widget.itemDoubleClicked, self.on_edit)
        return list_widget

    def create_root_layout(self):
        root_layout = QHBoxLayout()
        root_layout.addWidget(self.list_widget)
        root_layout.addLayout(self.make_control_buttons_layout())
        return root_layout

    def on_add(self):
        dialog = ItemSelectionDialog(self.available_items, title=self.available_items_title, parent=self)
        if dialog.exec_():
            self.list_widget.addItem(dialog.selected_text())

        self.items()

    def on_remove(self):
        if self.list_widget.currentItem().isSelected():
            self.list_widget.takeItem(self.list_widget.currentRow())

    def on_edit(self):
        if (current := self.list_widget.currentItem()).isSelected():
            new_text, ok = QInputDialog.getText(
                self.parent,
                'Edit',
                'New name:',
                text=current.text()
            )
            if ok:
                current.setText(new_text)

    def items(self) -> List[str]:
        return [self.list_widget.item(x).text() for x in range(self.list_widget.count())]

    def make_control_buttons_layout(self):
        def add():
            b = QPushButton('Add')
            qconnect(b.clicked, self.on_add)
            return b

        def remove():
            b = QPushButton('Remove')
            qconnect(b.clicked, self.on_remove)
            return b

        def edit():
            b = QPushButton('Edit️')
            qconnect(b.clicked, self.on_edit)
            return b

        layout = QVBoxLayout()
        layout.addWidget(add())
        layout.addWidget(remove())
        layout.addWidget(edit())
        layout.addStretch()
        return layout


class NoteTypesListEdit(ListEdit):
    def __init__(self, parent: QWidget):
        super(NoteTypesListEdit, self).__init__(
            parent=parent,
            items=config['note_types'],
            available_items=all_note_type_names(),
            available_items_title="Select Note Type",
        )


class SrcFieldsListEdit(ListEdit):
    def __init__(self, parent: QWidget):
        super(SrcFieldsListEdit, self).__init__(
            parent=parent,
            items=config['src_fields'],
            available_items=all_note_type_field_names(),
            available_items_title="Select Source Field",
        )


class DstFieldsListEdit(ListEdit):
    def __init__(self, parent: QWidget):
        super(DstFieldsListEdit, self).__init__(
            parent=parent,
            items=config['dst_fields'],
            available_items=all_note_type_field_names(),
            available_items_title="Select Destination Field",
        )


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
    NAME = 'Pitch Accent Options'

    def __init__(self, parent: QWidget):
        super(SettingsDialog, self).__init__(parent=parent or mw)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle(f'{ADDON_SERIES} {self.NAME}')
        self.setMinimumSize(420, 240)
        self.checkboxes = make_checkboxes()
        self.list_edits = {
            'note_types': NoteTypesListEdit(self),
            'src_fields': SrcFieldsListEdit(self),
            'dst_fields': DstFieldsListEdit(self),
        }
        self.setLayout(self.create_main_layout())
        self.load_config_values()

    def create_main_layout(self) -> QLayout:
        main = QVBoxLayout()
        main.addWidget(self.create_note_settings_layout())
        main.addLayout(self.create_checkboxes_layout())
        main.addStretch()
        main.addLayout(self.create_bottom_layout())
        return main

    def create_note_settings_layout(self):
        tabs_widget = QTabWidget()
        tabs_widget.addTab(self.list_edits['note_types'], "Note types")
        tabs_widget.addTab(self.list_edits['src_fields'], "Source fields")
        tabs_widget.addTab(self.list_edits['dst_fields'], "Destination fields")
        return tabs_widget

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
        for key, widget in self.list_edits.items():
            config[key] = widget.items()
        write_config()
        super(SettingsDialog, self).accept()


def create_options_action(parent: QWidget) -> QAction:
    def open_options():
        dialog = SettingsDialog(mw)
        return dialog.exec_()

    action = QAction(f'{SettingsDialog.NAME}...', parent)
    qconnect(action.triggered, open_options)
    return action
