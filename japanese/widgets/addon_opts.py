# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import typing
from collections.abc import Sequence

from aqt.qt import *

from ..ajt_common.monospace_line_edit import MONO_FONT_FAMILIES
from ..config_view import split_cfg_words
from ..helpers.consts import CFG_WORD_SEP

NARROW_WIDGET_MAX_WIDTH = 96


class AJTPlainTextEdit(QPlainTextEdit):
    """Plain text editor with AJT's compact monospace styling."""

    _min_height: int = 32
    _font_size: int = 14

    def __init__(self, parent: QWidget | None = None, initial_value: str = "") -> None:
        """Create a styled plain text editor with optional initial text."""
        super().__init__(parent)
        self.setMinimumHeight(self._min_height)
        self._adjust_font_size()
        self.set_text(initial_value)

    def _adjust_font_size(self) -> None:
        """Apply the configured monospace font family and compact size."""
        font = self.font()
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFamilies(MONO_FONT_FAMILIES)
        font.setPixelSize(self._font_size)
        self.setFont(font)

    def set_text(self, text: str) -> None:
        """Replace the editor text."""
        self.setPlainText(text)


class WordsEdit(AJTPlainTextEdit):
    """Plain text editor for comma-separated word lists."""

    def __init__(self, initial_values: Sequence[str], parent: QWidget | None = None) -> None:
        """Create the word-list editor from initial values."""
        super().__init__(parent)
        self.setPlaceholderText("Comma-separated list of words...")
        self.set_values(initial_values)

    def set_values(self, values: Sequence[str]) -> None:
        """Set unique word-list values while preserving their first occurrence order."""
        if not values:
            return
        self.set_text(CFG_WORD_SEP.join(dict.fromkeys(values)))

    def as_text(self) -> str:
        """Return a normalized comma-separated word list."""
        return CFG_WORD_SEP.join(split_cfg_words(self.toPlainText().replace(" ", "").replace("\n", CFG_WORD_SEP)))


class NarrowLineEdit(QLineEdit):
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setMaximumWidth(self._max_width)


class AllowedRange(typing.NamedTuple):
    min: int
    max: int


class NarrowSpinBox(QSpinBox):
    _allowed_range: AllowedRange = AllowedRange(1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(
        self,
        initial_value: int | None = None,
        allowed_range: AllowedRange | None = None,
        *args,
    ) -> None:
        super().__init__(*args)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        self.setSingleStep(1)
        if initial_value:
            self.setValue(initial_value)


class PxNarrowSpinBox(NarrowSpinBox):
    def __init__(
        self,
        initial_value: int | None = None,
        allowed_range: AllowedRange | None = None,
        *args,
    ) -> None:
        super().__init__(initial_value, allowed_range, *args)
        self.setSuffix(" px")


class AllowedRangeDouble(typing.NamedTuple):
    min: int | float
    max: int | float


class PxDoubleNarrowSpinBox(QDoubleSpinBox):
    _allowed_range: AllowedRangeDouble = AllowedRangeDouble(1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH
    _decimals: int = 2

    def __init__(
        self,
        initial_value: float | None = None,
        allowed_range: AllowedRangeDouble | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        self.setDecimals(self._decimals)
        self.setSuffix(" px")
        self.setSingleStep(1)
        if initial_value:
            self.setValue(initial_value)


class StrokeDisarrayLineEdit(NarrowLineEdit):
    """Only used to edit SVG devoiced stroke dasharray."""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        rx = QRegularExpression(r"^(?:\d+ )*\d+$")
        validator = QRegularExpressionValidator(rx)
        self.setValidator(validator)
