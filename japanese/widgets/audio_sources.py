# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import io
import re
from collections.abc import Iterable

from aqt.qt import *

from ..ajt_common.utils import clamp
from ..audio_manager.abstract import AudioSourceManagerFactoryABC
from ..audio_manager.basic_types import AudioSourceConfig
from ..audio_manager.source_manager import normalize_filename
from ..helpers.sqlite3_buddy import sqlite3_buddy
from .table import CellContent, ExpandingTableWidget, TableRow


class SourceEnableCheckbox(QCheckBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(
            """
        QCheckBox {
            margin: 0 auto;
        }
        """
        )


def tooltip_cache_remove_complete(removed: list[AudioSourceConfig]) -> None:
    from aqt import mw
    from aqt.utils import tooltip

    msg = io.StringIO()
    if removed:
        msg.write(f"<b>Removed {len(removed)} cache files:</b>")
        msg.write("<ol>")
        for source in removed:
            msg.write(f"<li>{source.name}</li>")
        msg.write("</ol>")
    else:
        msg.write("No cache files to remove")
    if mw:
        tooltip(msg.getvalue(), period=5000)


class AudioSourcesTable(ExpandingTableWidget):
    _columns = tuple(field.name.capitalize() for field in dataclasses.fields(AudioSourceConfig))
    # Slightly tightened the separator regex compared to the pitch override widget
    # since names and file paths can contain a wide range of characters.
    _sep_regex: re.Pattern = re.compile(r"[\r\t\n；;。、・]+", flags=re.IGNORECASE | re.MULTILINE)

    def __init__(self, audio_mgr: AudioSourceManagerFactoryABC, *args) -> None:
        super().__init__(*args)
        self._audio_mgr = audio_mgr
        self.addMoveRowContextActions()
        self.addClearCacheContextAction()

        # Override the parent class's section resize modes for some columns.
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def addClearCacheContextAction(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Clear cache for selected sources", self)
        qconnect(action.triggered, self.clearCacheForSelectedSources)
        self.addAction(action)

    def clearCacheForSelectedSources(self) -> None:
        """
        Remove cache files for the selected audio sources.
        Missing cache files are skipped.
        """
        removed: list[AudioSourceConfig] = []
        gui_selected_sources = [(selected.name, selected.url) for selected in self.iterateSelectedConfigs()]

        with sqlite3_buddy() as db:
            session = self._audio_mgr.request_new_session(db)
            for cached in session.audio_sources:
                if (cached.name, cached.url) in gui_selected_sources:
                    session.remove_data(cached.name)
                    removed.append(cached)
                    print(f"Removed cache for source: {cached.name} ({cached.url})")
                else:
                    print(f"Source isn't cached: {cached.name} ({cached.url})")
        tooltip_cache_remove_complete(removed)

    def addMoveRowContextActions(self) -> None:
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        def move_current_row(offset: int):
            current_row = self.currentRow()
            current_source_copy = pack_back(self.getRowCellContents(current_row))
            self.removeRow(current_row)
            self.addSource(
                current_source_copy,
                index=clamp(min_val=0, val=current_row + offset, max_val=self.rowCount() - 1),
            )

        action = QAction("Move row down", self)
        qconnect(action.triggered, lambda: move_current_row(1))
        self.addAction(action)

        action = QAction("Move row up", self)
        qconnect(action.triggered, lambda: move_current_row(-1))
        self.addAction(action)

        action = QAction("Move row to start", self)
        qconnect(action.triggered, lambda: move_current_row(-self.rowCount()))
        self.addAction(action)

        action = QAction("Move row to end", self)
        qconnect(action.triggered, lambda: move_current_row(self.rowCount()))
        self.addAction(action)

    def isCellFilled(self, cell: CellContent) -> bool:
        # A checked checkbox is considered filled,
        # so the user has to uncheck it to trigger an automatic row deletion.
        return isinstance(cell, QCheckBox) and cell.isChecked() or super().isCellFilled(cell)

    def addSource(self, source: AudioSourceConfig, index: int = None) -> None:
        self.addRow((checkbox := SourceEnableCheckbox(), source.name, source.url), index=index)
        # The checkbox widget has to notify the table widget when its state changes.
        # Otherwise, the table will not automatically add/remove rows.
        qconnect(checkbox.stateChanged, lambda checked: self.onCellChanged(self.currentRow()))
        checkbox.setChecked(source.enabled)

    def addEmptyLastRow(self) -> None:
        """Redefine this method."""
        return self.addSource(AudioSourceConfig(True, "", ""), index=self.rowCount())

    def iterateConfigs(self) -> Iterable[AudioSourceConfig]:
        """
        Return a list of source config objects. Ensure that names don't clash.
        """
        name_to_source: dict[str, AudioSourceConfig] = {}
        urls: set[str] = set()  # remember previously seen URLs
        for row in self.iterateRows():
            if all(row):
                source = pack_back(row)
                source.name = normalize_filename(source.name)
                if not source.name:
                    source.name = "unknown"
                while source.name in name_to_source:
                    source.name += "(new)"
                if source.is_valid and source.url not in urls:
                    name_to_source[source.name] = source
                    urls.add(source.url)
        return name_to_source.values()

    def iterateSelectedConfigs(self) -> Iterable[AudioSourceConfig]:
        selected_row_numbers = sorted(index.row() for index in self.selectedIndexes())
        for index, config in enumerate(self.iterateConfigs()):
            if index in selected_row_numbers:
                yield config

    def populate(self, sources: Iterable[AudioSourceConfig]) -> "AudioSourcesTable":
        self.setRowCount(0)
        for source in sources:
            self.addSource(source)
        return self

    def fillCellContent(self, row_n: int, col_n: int, content: str) -> None:
        if isinstance(cell := self.getCellContent(row_n, col_n), QCheckBox):
            return cell.setChecked(any(value in content.lower() for value in ("true", "yes", "y")))
        return super().fillCellContent(row_n, col_n, content)


def pack_back(row: TableRow) -> AudioSourceConfig:
    def to_json_compatible(item: CellContent):
        if isinstance(item, QCheckBox):
            return item.isChecked()
        return item.text()

    return AudioSourceConfig(*(to_json_compatible(item) for item in row))
