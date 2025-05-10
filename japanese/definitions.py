# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Optional

import requests
from aqt.editor import Editor
from aqt.qt import *

from .config_view import config_view as cfg
from .helpers.consts import ADDON_NAME
from .helpers.sakura_client import SakuraParisClient


@dataclasses.dataclass(frozen=True)
class WorkerResult:
    text: Optional[str] = None
    exception: Optional[Exception] = None


class WorkerSignals(QObject):
    result = pyqtSignal(WorkerResult)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._fn_args = args
        self._fn_kwargs = kwargs
        self.signals = WorkerSignals()

    def _emit_result(self, result: WorkerResult):
        self.signals.result.emit(result)  # type: ignore

    @pyqtSlot()
    def run(self):
        try:
            result = self._fn(*self._fn_args, **self._fn_kwargs)
        except requests.exceptions.ConnectionError:
            self._emit_result(WorkerResult(exception=RuntimeError("Connection error.")))
        except Exception as e:
            self._emit_result(WorkerResult(exception=e))
        else:
            self._emit_result(WorkerResult(text=result))


def create_progress_dialog(parent: QWidget):
    from aqt.progress import ProgressDialog

    dialog = ProgressDialog(parent)
    dialog.form.progressBar.setMinimum(0)
    dialog.form.progressBar.setMaximum(0)
    dialog.form.progressBar.setTextVisible(False)
    dialog.form.label.setText("Fetching definitions...")
    dialog.setWindowTitle(ADDON_NAME)
    dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
    dialog.setMinimumWidth(300)
    return dialog


class SakuraParisAnkiClient(SakuraParisClient):
    def add_definition(self, editor: Editor) -> None:
        """
        Interaction with Anki's editor.
        """
        from aqt.utils import tooltip

        for field_name in (self._config.source, self._config.destination):
            if field_name not in editor.note:
                return tooltip(f'Note doesn\'t have field "{field_name}".')
        if not editor.note[self._config.source]:
            return tooltip(f'Source field "{self._config.source}" is empty.')

        progress = create_progress_dialog(editor.parentWindow)

        def handle_result(result: WorkerResult):
            progress.accept()
            if result.exception:
                return tooltip(str(result.exception))
            elif not result.text:
                return tooltip("Nothing found.")
            else:
                editor.note[self._config.destination] = self._config.behavior.format(
                    field_value=editor.note[self._config.destination],
                    fetched_value=result.text,
                )
                return tooltip("Done.")

        # Set up
        worker = Worker(self.fetch_def, headword=editor.note[self._config.source])
        qconnect(worker.signals.result, handle_result)

        # Execute
        QThreadPool.globalInstance().start(worker)
        progress.exec()


# Entry point
##########################################################################

sakura_client = SakuraParisAnkiClient(cfg.definitions)
