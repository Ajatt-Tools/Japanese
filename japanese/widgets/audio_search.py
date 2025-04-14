# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import functools
import subprocess
import typing
from typing import cast

from anki.sound import SoundOrVideoTag
from anki.utils import no_bundled_libs
from aqt import mw, sound
from aqt.operations import QueryOp
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom, tooltip, tr

from ..ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from ..ajt_common.utils import find_executable, ui_translate
from ..audio_manager.abstract import AnkiAudioSourceManagerABC
from ..audio_manager.basic_types import FileUrlData
from ..audio_manager.download_results import (
    FileSaveResults,
    calc_tooltip_offset,
    format_report_errors_msg,
    format_report_results_msg,
)
from ..audio_manager.forvo_client import ForvoClient, FullForvoResult
from ..helpers.consts import ADDON_NAME
from ..helpers.file_ops import open_file
from ..helpers.misc import strip_html_and_media
from .audio_serach_result_label import AudioSearchResultLabel
from .audio_sources import SourceEnableCheckbox

if mw is None:

    def strip_html_and_media(text: str) -> str:
        return text  # noop


class FileSaveResultsProtocol(typing.Protocol):
    successes: list
    fails: list


class SearchBar(QWidget):
    """
    Combines a line edit and a search button.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_line = QLineEdit()
        self._search_button = QPushButton("Search")
        qconnect(self._search_line.returnPressed, self._search_button.click)
        self._init_ui()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            return
        return super().keyPressEvent(event)

    @property
    def search_committed(self) -> pyqtSignal:
        return self._search_button.clicked

    def current_text(self) -> str:
        return self._search_line.text()

    def set_text(self, text: str) -> None:
        self._search_line.setText(text)

    def _init_ui(self) -> None:
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(3)
        hbox.addWidget(self._search_line)
        hbox.addWidget(self._search_button)
        self._search_line.setPlaceholderText("Word to look up...")
        self.setLayout(hbox)


@enum.unique
class SearchResultsTableColumns(enum.Enum):
    add_to_note = 0
    play_audio = enum.auto()
    open_audio = enum.auto()
    source_name = enum.auto()
    word = enum.auto()
    reading = enum.auto()
    pitch_number = enum.auto()
    filename = enum.auto()

    @classmethod
    def column_count(cls):
        return sum(1 for _ in cls)


class SearchResultsTable(QTableWidget):
    play_requested = pyqtSignal(FileUrlData)
    open_requested = pyqtSignal(FileUrlData)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_results: list[FileUrlData] = []
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setColumnCount(SearchResultsTableColumns.column_count())
        self.setHorizontalHeaderLabels(ui_translate(item.name) for item in SearchResultsTableColumns)
        self.setSectionResizeModes()

    def setSectionResizeModes(self):
        contents = QHeaderView.ResizeMode.ResizeToContents
        hor_header = self.horizontalHeader()

        for column_number in (item.value for item in SearchResultsTableColumns):
            hor_header.setSectionResizeMode(column_number, contents)

    def clear(self):
        self.setRowCount(0)
        self._last_results.clear()

    def files_to_add(self) -> list[FileUrlData]:
        to_add = []
        for row_n, result in zip(range(self.rowCount()), self._last_results):
            checkbox = typing.cast(QCheckBox, self.cellWidget(row_n, SearchResultsTableColumns.add_to_note.value))
            if checkbox.isChecked():
                to_add.append(result)
        return to_add

    def populate_with_results(self, results: list[FileUrlData]):
        for row_n, file in enumerate(results, start=len(self._last_results)):
            self.insertRow(row_n)
            self.setCellWidget(row_n, SearchResultsTableColumns.add_to_note.value, SourceEnableCheckbox())
            self.setCellWidget(row_n, SearchResultsTableColumns.play_audio.value, pb := QPushButton("Play"))
            self.setCellWidget(row_n, SearchResultsTableColumns.open_audio.value, ob := QPushButton("Open"))
            row_map = {
                SearchResultsTableColumns.source_name: file.source_name,
                SearchResultsTableColumns.word: file.word,
                SearchResultsTableColumns.reading: file.reading,
                SearchResultsTableColumns.pitch_number: file.pitch_number,
                SearchResultsTableColumns.filename: file.desired_filename,
            }
            for column, field in row_map.items():
                self.setItem(row_n, column.value, item := QTableWidgetItem(field))
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            qconnect(pb.clicked, functools.partial(self.play_requested.emit, file))  # type:ignore
            qconnect(ob.clicked, functools.partial(self.open_requested.emit, file))  # type:ignore
        # remember results
        self._last_results.extend(results)


class SearchLock:
    """
    Class used to indicate that a search operation is in progress.
    Until a search operation finishes, don't allow subsequent searches.
    """

    def __init__(self, search_bar: SearchBar) -> None:
        self._search_bar = search_bar
        self._is_searching = False

    def set_searching(self, searching: bool) -> None:
        self._is_searching = searching
        self._search_bar.setDisabled(searching)

    def is_searching(self) -> bool:
        return self._is_searching


class AudioSearchDialog(QDialog):
    _audio_manager: AnkiAudioSourceManagerABC
    _forvo_client: ForvoClient

    def __init__(self, audio_manager: AnkiAudioSourceManagerABC, forvo_client: ForvoClient, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setWindowTitle(f"{ADDON_NAME} - Audio search")
        self._audio_manager = audio_manager
        self._forvo_client = forvo_client

        # create widgets
        self._search_bar = SearchBar()
        self._src_field_selector = QComboBox()
        self._dest_field_selector = QComboBox()
        self._table_widget = SearchResultsTable()
        self._search_result_label = AudioSearchResultLabel()
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Add audio and close")

        # Create lock.
        self._search_lock = SearchLock(self._search_bar)

        # add search bar, button, and table to main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(self._create_top_layout())
        main_layout.addWidget(self._table_widget)
        main_layout.addWidget(self._search_result_label)
        main_layout.addWidget(self._button_box)
        self.setLayout(main_layout)

        # connect search button to search function
        qconnect(self._search_bar.search_committed, lambda: self.search())
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)
        qconnect(self._table_widget.play_requested, self._play_audio_file)
        qconnect(self._table_widget.open_requested, self._open_audio_file)

    def _play_audio_file(self, file: FileUrlData):
        """
        This method requires Anki to be running.
        """
        pass

    def _open_audio_file(self, file: FileUrlData):
        """
        This method requires Anki to be running.
        """
        if opener := find_executable("xdg-open"):
            subprocess.Popen(
                [opener, file.url],
                shell=False,
                start_new_session=True,
            )

    def _create_top_layout(self) -> QLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Source:"))
        layout.addWidget(self._src_field_selector)
        layout.addWidget(QLabel("Destination:"))
        layout.addWidget(self._dest_field_selector)
        layout.addWidget(QLabel("Search:"))
        layout.addWidget(self._search_bar)
        for combo in (self._src_field_selector, self._dest_field_selector):
            combo.setMinimumWidth(120)
            combo.setMaximumWidth(200)
            combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        cast(QDialog, self._search_bar).setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        return layout

    @property
    def table(self) -> SearchResultsTable:
        return self._table_widget

    def files_to_add(self) -> list[FileUrlData]:
        return self._table_widget.files_to_add()

    def search(self, search_text: typing.Optional[str] = None) -> None:
        if self._search_lock.is_searching():
            return
        self._table_widget.clear()
        # strip media in case source field and destination field are the same.
        search_text = strip_html_and_media(search_text or self._search_bar.current_text())
        self._search_bar.set_text(search_text)
        if not search_text:
            return
        # repopulate with new data
        self._table_widget.populate_with_results(
            self._audio_manager.search_audio(
                search_text,
                split_morphemes=True,
                ignore_inflections=False,
                stop_if_one_source_has_results=False,
            )
        )
        # search Forvo
        self._search_forvo(search_text)

    def _search_forvo(self, search_text: str) -> None:
        """
        Search audio files on the Forvo website.
        """
        results = self._forvo_client.full_search(search_text)
        self._table_widget.populate_with_results(results.files)
        self._search_result_label.set_count(results)

    def set_note_fields(
        self,
        field_names: list[str],
        *,
        selected_src_field_name: str,
        selected_dest_field_name: str,
    ) -> None:
        for combo in (self._src_field_selector, self._dest_field_selector):
            combo.clear()
            combo.addItems(field_names)
        self._src_field_selector.setCurrentText(selected_src_field_name)
        self._dest_field_selector.setCurrentText(selected_dest_field_name)

    @property
    def source_field_name(self) -> str:
        return self._src_field_selector.currentText()

    @property
    def destination_field_name(self) -> str:
        return self._dest_field_selector.currentText()


class AnkiAudioSearchDialog(AudioSearchDialog):
    name: str = "ajt__audio_search_dialog"

    def __init__(self, audio_manager: AnkiAudioSourceManagerABC, forvo_client: ForvoClient, parent=None) -> None:
        super().__init__(audio_manager, forvo_client, parent)
        # Restore previous geom
        restoreGeom(self, self.name, adjustSize=True)

    def _play_audio_file(self, file: FileUrlData) -> None:
        if os.path.isfile(file.url):
            return sound.av_player.play_tags([SoundOrVideoTag(filename=file.url)])
        elif mw.col.media.have(file.desired_filename):
            return sound.av_player.play_tags([SoundOrVideoTag(filename=file.desired_filename)])
        else:
            # file is not located on this computer and needs to be downloaded first.
            self._search_result_label.set_downloading(file.desired_filename)
            return self._audio_manager.download_and_save_tags(
                hits=[file],
                on_finish=self._handle_and_play_download_result,
            )

    def _handle_and_play_download_result(self, results: FileSaveResults):
        self._search_result_label.hide_count()
        sound.av_player.play_tags(
            [SoundOrVideoTag(filename=result.desired_filename) for result in results.successes]
        )
        if results.fails and (txt := format_report_errors_msg(results.fails)):
            return tooltip(msg=txt, parent=self, period=7000, y_offset=calc_tooltip_offset(len(results.fails)))

    def _open_audio_file(self, file: FileUrlData) -> None:
        tooltip(tr.qt_misc_loading(), period=1000)

        if os.path.isfile(file.url):
            return open_file(file.url)
        elif mw.col.media.have(file.desired_filename):
            return open_file(os.path.join(mw.col.media.dir(), file.desired_filename))
        else:
            with no_bundled_libs():
                QDesktopServices.openUrl(QUrl(file.url))

    def done(self, *args, **kwargs) -> None:
        saveGeom(self, self.name)
        return super().done(*args, **kwargs)

    def _search_forvo(self, search_text: str) -> None:
        """
        Search audio files on the Forvo website.
        """
        if self._search_lock.is_searching():
            return

        self._search_result_label.hide_count()

        def search_on_forvo(_col) -> FullForvoResult:
            """
            Search and collect results from Forvo
            """
            return self._forvo_client.full_search(search_text)

        def set_search_results(results: FullForvoResult) -> None:
            self._table_widget.populate_with_results(results.files)
            self._search_result_label.set_count(results)
            self._search_lock.set_searching(False)

        def on_exception(exception: Exception) -> None:
            self._search_lock.set_searching(False)
            self._search_result_label.set_error(exception)

        self._search_lock.set_searching(True)
        (
            QueryOp(
                parent=self,
                op=search_on_forvo,
                success=set_search_results,
            )
            .failure(on_exception)
            .without_collection()
            .run_in_background()
        )
