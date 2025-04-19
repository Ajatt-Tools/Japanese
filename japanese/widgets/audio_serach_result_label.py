# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import enum
import io
from typing import Optional

import requests
from aqt.qt import *

from ..audio_manager.forvo_client import ForvoClientException, FullForvoResult


@enum.unique
class ForvoSearchResult(enum.Enum):
    ok = "green"
    warn = "orange"
    error = "red"
    default = "black"


def explain_error(ex: Exception) -> str:
    if isinstance(ex, ForvoClientException):
        return ex.explanation
    else:
        return f"Unknown error: {ex}"


def is_not_found(ex: Exception) -> bool:
    return (
        isinstance(ex, ForvoClientException)
        and ex.response is not None
        and ex.response.status_code == requests.codes.not_found
    )


def is_serious_error(ex: Optional[Exception]) -> bool:
    return ex is not None and not is_not_found(ex)


class AudioSearchResultLabel(QLabel):
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Maximum)
        self.hide_count()

    def hide_count(self) -> None:
        self.setText("")
        self.setStyleSheet("")
        self.hide()

    def _set_status_text(self, text: str, status: ForvoSearchResult):
        self.setText(text)
        self.setStyleSheet("QLabel { color: %s; }" % status.value)
        if self.isHidden():
            self.show()

    def set_error(self, ex: Exception) -> None:
        if is_not_found(ex):
            self._set_status_text("Forvo: no results found.", ForvoSearchResult.warn)
        elif isinstance(ex, ForvoClientException):
            self._set_status_text(ex.explanation, ForvoSearchResult.error)
        else:
            self._set_status_text(f"Forvo error: {ex}", ForvoSearchResult.error)

    def set_nothing_to_do(self) -> None:
        self._set_status_text("Search query is empty. Did nothing.", ForvoSearchResult.warn)

    def set_downloading(self, filename: str) -> None:
        self._set_status_text(f"Downloading file '{filename}'", ForvoSearchResult.default)

    def set_count(self, result: FullForvoResult) -> None:
        status = ForvoSearchResult.ok
        message = io.StringIO()
        if len(result.files) > 0:
            message.write(f"Forvo: {len(result.files)} files found.")
        else:
            message.write(f"Forvo: nothing found.")
            status = ForvoSearchResult.warn

        if is_serious_error(result.error_search):
            message.write(f" Search: {explain_error(result.error_search)}.")
            status = ForvoSearchResult.error

        if is_serious_error(result.error_word):
            message.write(f" Word: {explain_error(result.error_word)}.")
            status = ForvoSearchResult.error

        return self._set_status_text(message.getvalue(), status)
