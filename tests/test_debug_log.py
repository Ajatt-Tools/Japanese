# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import logging
from collections.abc import Iterable

import pytest

from japanese.helpers import debug_log


@pytest.fixture
def clean_addon_logger() -> Iterable[logging.Logger]:
    """Yield the shared add-on logger with handlers and propagation reset."""
    logger = debug_log.AddonManager.get_logger(debug_log.__name__)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.propagate = True
    yield logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.propagate = True


class TestGetLogger:
    """get_logger returns Anki's add-on logger with messages visible by default."""

    def test_sets_debug_level(self, clean_addon_logger: logging.Logger) -> None:
        """The add-on logger is set to DEBUG so diagnostic messages are not dropped."""
        assert debug_log.get_logger().level == logging.DEBUG

    def test_attaches_single_stream_handler_outside_anki(self, clean_addon_logger: logging.Logger) -> None:
        """Outside Anki, one stderr handler is attached; a second call adds none."""
        debug_log.get_logger()
        debug_log.get_logger()
        assert len(clean_addon_logger.handlers) == 1
        assert isinstance(clean_addon_logger.handlers[0], logging.StreamHandler)

    def test_disables_propagation_outside_anki(self, clean_addon_logger: logging.Logger) -> None:
        """Propagation is disabled outside Anki so messages are not duplicated."""
        debug_log.get_logger()
        assert clean_addon_logger.propagate is False

    def test_no_stream_handler_when_anki_runs(
        self, clean_addon_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When Anki is running, Anki's own log handler is used and no stderr handler is added."""
        monkeypatch.setattr(debug_log, "mw", object())
        debug_log.get_logger()
        assert clean_addon_logger.handlers == []
