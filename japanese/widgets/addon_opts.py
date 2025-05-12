# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Sequence
from typing import Optional

from aqt.qt import *

from ..config_view import split_cfg_words
from ..helpers.consts import CFG_WORD_SEP

NARROW_WIDGET_MAX_WIDTH = 96


class WordsEdit(QTextEdit):
    _min_height = 32
    _font_size = 16

    def __init__(self, initial_values: Sequence[str]) -> None:
        super().__init__()
        self.setAcceptRichText(False)
        self.set_values(initial_values)
        self.setMinimumHeight(self._min_height)
        self._adjust_font_size()
        self.setPlaceholderText("Comma-separated list of words...")

    def _adjust_font_size(self):
        font = self.font()
        font.setPixelSize(self._font_size)
        self.setFont(font)

    def set_values(self, values: Sequence[str]):
        if values:
            self.setPlainText(CFG_WORD_SEP.join(dict.fromkeys(values)))

    def as_text(self) -> str:
        return CFG_WORD_SEP.join(split_cfg_words(self.toPlainText().replace(" ", "").replace("\n", CFG_WORD_SEP)))


class NarrowLineEdit(QLineEdit):
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setMaximumWidth(self._max_width)


class NarrowSpinBox(QSpinBox):
    _allowed_range: tuple[int, int] = (1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH

    def __init__(
        self,
        initial_value: Optional[int] = None,
        allowed_range: Optional[tuple[int, int]] = None,
        *args,
    ) -> None:
        super().__init__(*args)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        if initial_value:
            self.setValue(initial_value)


class PxNarrowSpinBox(NarrowSpinBox):
    def __init__(
        self,
        initial_value: Optional[int] = None,
        allowed_range: Optional[tuple[int, int]] = None,
        *args,
    ) -> None:
        super().__init__(initial_value, allowed_range, *args)
        self.setSuffix(" px")


class PxDoubleNarrowSpinBox(QDoubleSpinBox):
    _allowed_range: tuple[float, float] = (1, 99)
    _max_width: int = NARROW_WIDGET_MAX_WIDTH
    _decimals: int = 2

    def __init__(
        self,
        initial_value: Optional[float] = None,
        allowed_range: Optional[tuple[float, float]] = None,
        *args,
    ) -> None:
        super().__init__(*args)
        self._allowed_range = allowed_range or self._allowed_range
        self.setRange(*self._allowed_range)
        self.setMaximumWidth(self._max_width)
        self.setDecimals(self._decimals)
        self.setSuffix(" px")
        if initial_value:
            self.setValue(initial_value)


class StrokeDisarrayLineEdit(NarrowLineEdit):
    """Only used to edit SVG devoiced stroke dasharray."""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        rx = QRegularExpression(r"^(\d+ )*\d+$")
        validator = QRegularExpressionValidator(rx)
        self.setValidator(validator)
