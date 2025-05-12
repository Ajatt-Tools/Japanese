# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Iterable
from types import SimpleNamespace
from typing import Optional

from aqt.qt import *

from ..ajt_common.addon_config import ConfigSubViewBase
from ..ajt_common.anki_field_selector import AnkiFieldSelector
from ..ajt_common.enum_select_combo import EnumSelectCombo
from ..ajt_common.grab_key import ShortCutGrabButton
from ..ajt_common.utils import q_emit, ui_translate
from ..config_view import (
    AudioSettingsConfigView,
    ContextMenuConfigView,
    DefinitionsConfigView,
    ForvoSettingsConfigView,
    FuriganaConfigView,
    PitchConfigView,
    SvgPitchGraphOptionsConfigView,
)
from ..helpers.misc import split_list
from ..helpers.sakura_client import AddDefBehavior, DictName, SearchType
from ..pitch_accents.styles import HTMLPitchPatternStyle
from .addon_opts import (
    NarrowLineEdit,
    NarrowSpinBox,
    PxDoubleNarrowSpinBox,
    PxNarrowSpinBox,
    StrokeDisarrayLineEdit,
    WordsEdit,
)
from .widgets_to_config_dict import as_config_dict


class SettingsForm(QWidget):
    _config: Optional[ConfigSubViewBase] = None
    _title: Optional[str] = None

    def __init__(self, config: Optional[ConfigSubViewBase] = None, title: Optional[str] = None):
        super().__init__()
        self._title = title or self._title
        self._config = config or self._config

        assert self._title, "Title must be set."
        assert self._config, "Config must be set."

        self._widgets = SimpleNamespace()
        self._add_widgets()
        self._add_tooltips()
        self.setLayout(self._make_layout())

    @property
    def title(self) -> str:
        assert self._title
        return self._title

    def _add_widgets(self) -> None:
        """Subclasses add new widgets here."""
        self._widgets.__dict__.update(self._create_checkboxes())

    def _add_tooltips(self) -> None:
        """Subclasses add new tooltips here."""
        pass

    def as_dict(self) -> dict[str, Union[bool, str, int]]:
        return as_config_dict(self._widgets.__dict__)

    def _create_checkboxes(self) -> Iterable[tuple[str, QCheckBox]]:
        assert self._config
        for key, value in self._config.toggleables():
            checkbox = QCheckBox(ui_translate(key))
            checkbox.setChecked(value)
            yield key, checkbox

    def _make_layout(self) -> QLayout:
        layout = QFormLayout()
        for key, widget in self._widgets.__dict__.items():
            if isinstance(widget, QCheckBox):
                layout.addRow(widget)
            else:
                layout.addRow(ui_translate(key), widget)
        return layout


class DefinitionsSettingsForm(SettingsForm):
    _config: DefinitionsConfigView
    _title: str = "Add definition"

    def _add_widgets(self) -> None:
        super()._add_widgets()
        self._widgets.source = AnkiFieldSelector(
            initial_value=self._config.source,
        )
        self._widgets.destination = AnkiFieldSelector(
            initial_value=self._config.destination,
        )
        self._widgets.dict_name = EnumSelectCombo(
            enum_type=DictName,
            initial_value=self._config.dict_name,
            show_values=True,
        )
        self._widgets.search_type = EnumSelectCombo(
            enum_type=SearchType,
            initial_value=self._config.search_type,
        )
        self._widgets.behavior = EnumSelectCombo(
            enum_type=AddDefBehavior,
            initial_value=self._config.behavior,
        )
        self._widgets.timeout = NarrowSpinBox(
            initial_value=self._config.timeout,
        )

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.timeout.setToolTip(
            "Download timeout in seconds.",
        )
        self._widgets.remove_marks.setToolTip(
            "Strip all <mark> tags from definitions.\n"
            "Usually <mark> tags simply repeat the headword and are not needed."
        )
        self._widgets.dict_name.setToolTip(
            "Dictionary to fetch definitions from.",
        )
        self._widgets.search_type.setToolTip(
            "How to search.\n"
            "Prefix — headwords starting with the search string.\n"
            "Suffix — headwords ending with the search string.\n"
            "Exact — headwords equal to the search string."
        )
        self._widgets.behavior.setToolTip(
            "How to add fetched definitions.\nReplace existing definitions, append or prepend."
        )


class MultiColumnSettingsForm(SettingsForm):
    _columns: int = 3
    _alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    _widget_min_height: int = 25
    _column_spacing: int = 16
    _equal_col_width: bool = False

    def _make_layout(self) -> QLayout:
        layout = QHBoxLayout()
        layout.setSpacing(self._column_spacing)
        form: QFormLayout
        for index, chunk in enumerate(split_list(list(self._widgets.__dict__.items()), self._columns)):
            layout.addLayout(form := QFormLayout())
            form.setAlignment(self._alignment)
            widget: QWidget
            for key, widget in chunk:
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                widget.setMinimumHeight(max(widget.minimumHeight(), self._widget_min_height))
                if isinstance(widget, QCheckBox):
                    form.addRow(widget)
                else:
                    form.addRow(ui_translate(key), widget)
            if self._equal_col_width:
                layout.setStretch(index, 1)
        return layout


class ContextMenuSettingsForm(MultiColumnSettingsForm):
    _columns: int = 2
    _config: ContextMenuConfigView
    _title: str = "Context menu"

    def _add_tooltips(self):
        super()._add_tooltips()
        for action in self._widgets.__dict__.values():
            action.setToolTip("Show this action in the context menu.")


class PitchSettingsForm(MultiColumnSettingsForm):
    _title: str = "Pitch Options"
    _config: PitchConfigView

    def _add_widgets(self) -> None:
        super()._add_widgets()
        self._widgets.maximum_results = NarrowSpinBox(
            initial_value=self._config.maximum_results,
        )
        self._widgets.html_style = EnumSelectCombo(
            enum_type=HTMLPitchPatternStyle,
            initial_value=self._config.html_style,
        )
        self._widgets.reading_separator = NarrowLineEdit(self._config.reading_separator)
        self._widgets.word_separator = NarrowLineEdit(self._config.word_separator)
        self._widgets.lookup_shortcut = ShortCutGrabButton(initial_value=self._config.lookup_shortcut)
        self._widgets.lookup_pitch_format = EnumSelectCombo(initial_value=self._config.lookup_pitch_format)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.output_hiragana.setToolTip(
            "Print pitch accents using hiragana.\nNormally katakana is used to print pitch accent."
        )
        self._widgets.kana_lookups.setToolTip(
            "Attempt to look up a word using its kana reading\nif there's no entry for its kanji form."
        )
        self._widgets.skip_numbers.setToolTip(
            "Don't add pitch accents to numbers.\nIf enabled, numbers won't be color-coded in furigana as well."
        )
        self._widgets.reading_separator.setToolTip("String used to separate multiple accents of a word.")
        self._widgets.word_separator.setToolTip("String used to separate multiple words.")
        self._widgets.blocklisted_words.setToolTip("A comma-separated list of words that won't be looked up.")
        self._widgets.maximum_results.setToolTip(
            "Maximum number of results to output.\nToo many results are not informative and will bloat Anki cards."
        )
        self._widgets.lookup_shortcut.setToolTip("A keyboard shortcut for looking up selected text.")
        self._widgets.lookup_pitch_format.setToolTip(
            "Pitch output format used when the lookup window is shown.\nHas no effect on Profiles."
        )
        self._widgets.html_style.setToolTip(
            "Style of pitch accent patterns.\n"
            'If set to "none", you can configure your own styles\n'
            "in the Styling section of your card type using CSS class names."
        )


class FuriganaSettingsForm(MultiColumnSettingsForm):
    _title: str = "Furigana Options"
    _config: FuriganaConfigView

    def _add_widgets(self) -> None:
        super()._add_widgets()
        self._widgets.maximum_results = NarrowSpinBox(initial_value=self._config.maximum_results)
        self._widgets.maximum_pitch_accents = NarrowSpinBox(initial_value=self._config.maximum_pitch_accents)
        self._widgets.reading_separator = NarrowLineEdit(self._config.reading_separator)
        self._widgets.blocklisted_words = WordsEdit(initial_values=self._config.blocklisted_words)
        self._widgets.mecab_only = WordsEdit(initial_values=self._config.mecab_only)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.skip_numbers.setToolTip("Don't add furigana to numbers.")
        self._widgets.prefer_literal_pronunciation.setToolTip(
            "Print furigana in a way that shows a word's literal pronunciation."
        )
        self._widgets.reading_separator.setToolTip(
            "String used to separate multiple readings of a word.\n\n"
            "Note that to show more than one reading over a word\n"
            "you need to import a compatible Note Type,\n"
            "like the one provided by Ajatt-Tools."
        )
        self._widgets.blocklisted_words.setToolTip(
            "A comma-separated list of words that won't be looked up.\nFurigana won't be added."
        )
        self._widgets.mecab_only.setToolTip(
            "A comma-separted list of words that won't be looked up in the bundled dictionary.\n"
            "However, they will still be looked up using Mecab."
        )
        self._widgets.maximum_results.setToolTip(
            "Maximum number of results to output.\nToo many results are not informative and will bloat Anki cards."
        )


class AudioSettingsForm(MultiColumnSettingsForm):
    _title: str = "Audio settings"
    _config: AudioSettingsConfigView

    def _add_widgets(self) -> None:
        super()._add_widgets()
        self._widgets.dictionary_download_timeout = NarrowSpinBox(
            initial_value=self._config.dictionary_download_timeout
        )
        self._widgets.audio_download_timeout = NarrowSpinBox(initial_value=self._config.audio_download_timeout)
        self._widgets.attempts = NarrowSpinBox(initial_value=self._config.attempts)
        self._widgets.maximum_results = NarrowSpinBox(initial_value=self._config.maximum_results)
        self._widgets.tag_separator = NarrowLineEdit(self._config.tag_separator)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.dictionary_download_timeout.setToolTip("Download timeout in seconds.")
        self._widgets.audio_download_timeout.setToolTip("Download timeout in seconds.")
        self._widgets.attempts.setToolTip(
            "Number of attempts before giving up.\nApplies to both dictionary downloads and audio downloads."
        )
        self._widgets.ignore_inflections.setToolTip(
            "If enabled, audio recordings of inflected readings won't be added."
        )
        self._widgets.stop_if_one_source_has_results.setToolTip(
            "If enabled, stop searching after audio files were found in at least one source.\n"
            "The order of sources in the table matters."
        )
        self._widgets.maximum_results.setToolTip(
            "Maximum number of audio files to add.\n\n"
            "Note: If a word has several pitch accents,\n"
            "this setting may result in some of them not being represented."
        )
        self._widgets.tag_separator.setToolTip(
            "Separate [sound:filename.ogg] tags with this string\nwhen adding audio files to cards."
        )


class ForvoSettingsForm(SettingsForm):
    _title: str = "Forvo settings (Audio Search)"
    _config: ForvoSettingsConfigView

    def _add_widgets(self) -> None:
        super()._add_widgets()
        self._widgets.language = NarrowLineEdit(self._config.language)
        self._widgets.preferred_usernames = WordsEdit(initial_values=self._config.preferred_usernames)
        self._widgets.preferred_countries = WordsEdit(initial_values=self._config.preferred_countries)
        self._widgets.timeout_seconds = NarrowSpinBox(initial_value=self._config.timeout_seconds)
        self._widgets.retry_attempts = NarrowSpinBox(initial_value=self._config.retry_attempts)
        self._widgets.audio_format = EnumSelectCombo(initial_value=self._config.audio_format)

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.show_gender.setToolTip("Add the user's gender to the filename.")
        self._widgets.show_country.setToolTip("Add the user's country to the filename.")
        self._widgets.language.setToolTip(
            'Audio language. Other languages will be skipped.\n"ja" for Japanese, "zh" for Mandarin, etc.'
        )
        self._widgets.timeout_seconds.setToolTip("Download timeout in seconds.")
        self._widgets.retry_attempts.setToolTip("Number of attempts before giving up.")
        self._widgets.preferred_usernames.setToolTip("A comma-separated list of usernames that will be sorted higher.")
        self._widgets.preferred_countries.setToolTip("A comma-separated list of countries that will be sorted higher.")


SvgOptValueType = type[Union[int, float]]
SvgOptSpinbox = Union[PxNarrowSpinBox, PxDoubleNarrowSpinBox]


class SvgSettingsForm(MultiColumnSettingsForm):
    _columns: int = 2
    _title: str = "SVG settings"
    _config: SvgPitchGraphOptionsConfigView
    _value_type_to_widget_type: dict[SvgOptValueType, type[SvgOptSpinbox]] = {
        int: PxNarrowSpinBox,
        float: PxDoubleNarrowSpinBox,
    }
    opts_changed = pyqtSignal()

    def _create_spinboxes(self) -> Iterable[tuple[str, SvgOptSpinbox]]:
        assert self._config
        spinbox: SvgOptSpinbox
        # skipped options have different defaults and will be handled separately
        skip_keys = (
            "text_dx",
            "tspan_dx",
            "x_step",
            "devoiced_circle_dy",
            "devoiced_rectangle_padding",
            "letter_spacing",
        )
        for key, value in self._config.items():
            if key in skip_keys:
                continue
            try:
                spinbox = self._value_type_to_widget_type[type(value)](
                    initial_value=value,
                    allowed_range=(0, 999),
                )
                yield key, spinbox
            except KeyError:
                pass

    def _add_widgets(self) -> None:
        super()._add_widgets()

        # dy/dx are allowed to be negative.
        self._widgets.text_dx = PxNarrowSpinBox(initial_value=self._config.text_dx, allowed_range=(-999, 999))
        self._widgets.letter_spacing = PxDoubleNarrowSpinBox(
            initial_value=self._config.letter_spacing, allowed_range=(-999, 999)
        )
        self._widgets.tspan_dx = PxNarrowSpinBox(initial_value=self._config.tspan_dx, allowed_range=(-999, 999))

        # x step can't be 0 because it will cause division by zero.
        self._widgets.x_step = PxNarrowSpinBox(initial_value=self._config.x_step, allowed_range=(1, 999))

        self._widgets.__dict__.update(self._create_spinboxes())
        self._widgets.devoiced_circle_dy = PxNarrowSpinBox(
            initial_value=self._config.devoiced_circle_dy, allowed_range=(-999, 999)
        )
        self._widgets.devoiced_rectangle_padding = PxDoubleNarrowSpinBox(
            initial_value=self._config.devoiced_rectangle_padding, allowed_range=(-999, 999)
        )
        self._widgets.devoiced_stroke_dasharray = StrokeDisarrayLineEdit(self._config.devoiced_stroke_dasharray)
        self._connect_widgets()

    def _connect_widgets(self) -> None:
        for widget in self._widgets.__dict__.values():
            if isinstance(widget, QCheckBox):
                # checkStateChanged in pyqt 6.7+
                qconnect(widget.stateChanged, lambda: q_emit(self.opts_changed))
            elif isinstance(widget, QAbstractSpinBox):
                qconnect(widget.valueChanged, lambda: q_emit(self.opts_changed))
            elif isinstance(widget, QLineEdit):
                qconnect(widget.textChanged, lambda: q_emit(self.opts_changed))
            else:
                raise ValueError(f"Unhandled widget type: {type(widget)}")

    def _add_tooltips(self) -> None:
        super()._add_tooltips()
        self._widgets.graph_horizontal_padding.setToolTip("Padding to the left and right of the image.")
        self._widgets.devoiced_stroke_dasharray.setToolTip(
            "Pattern of dashes and gaps used to paint\nthe outline of the devoiced circle."
        )
