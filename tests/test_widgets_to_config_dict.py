# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
from collections.abc import Callable
from typing import Any

import pytest
from aqt.qt import *

try:
    QTest
except NameError:
    from PyQt6.QtTest import QTest

from japanese.ajt_common.color_picker import ColorEditPicker
from japanese.ajt_common.enum_select_combo import EnumSelectCombo
from japanese.ajt_common.grab_key import ShortCutGrabButton
from japanese.config_view import SvgGraphReadingFormat
from japanese.widgets.addon_opts import (
    AJTPlainTextEdit,
    PxDoubleNarrowSpinBox,
    PxNarrowSpinBox,
    StrokeDisarrayLineEdit,
    WordsEdit,
)
from japanese.widgets.enum_selector import FlagSelectCombo
from japanese.widgets.settings_form import SvgSettingsForm
from japanese.widgets.svg_settings import (
    DEBOUNCE_UPDATE_VIEW_MS,
    SVG_SETTINGS_BODY_VERTICAL_PADDING,
    SvgSettingsWidget,
)
from japanese.widgets.widgets_to_config_dict import (
    as_config_dict,
    change_event,
    get_from_widget,
    set_from_cfg,
)
from playground.utils import NoAnkiConfigView


@enum.unique
class _TestFlags(enum.Flag):
    none = enum.auto()
    foo = enum.auto()
    bar = enum.auto()


class TestSetFromCfg:
    @pytest.mark.parametrize(
        "widget_factory, value",
        [
            (QDoubleSpinBox, 42.0),
            (QSpinBox, 13),
            (QLineEdit, "hello"),
            (QPlainTextEdit, "Noto Sans"),
            (QCheckBox, True),
            (QCheckBox, False),
        ],
    )
    def test_set_value(self, widget_factory: Callable[[], QWidget], value: float | int | str | bool) -> None:
        widget = widget_factory()
        set_from_cfg(widget, value)
        assert get_from_widget(widget) == value

    def test_set_enum_select_combo(self) -> None:
        widget = EnumSelectCombo(enum_type=SvgGraphReadingFormat)
        set_from_cfg(widget, SvgGraphReadingFormat.hiragana)
        assert get_from_widget(widget) == SvgGraphReadingFormat.hiragana.name

    def test_set_qcombobox(self) -> None:
        widget = QComboBox()
        widget.addItems(["a", "b", "c"])
        set_from_cfg(widget, "b")
        assert get_from_widget(widget) == "b"

    def test_unknown_type_raises(self) -> None:
        widget = QWidget()
        with pytest.raises(ValueError, match="Can't handle widget"):
            set_from_cfg(widget, 42)


class TestGetFromWidget:
    @pytest.mark.parametrize(
        "widget_factory, expected_value, setup",
        [
            (QDoubleSpinBox, 5.0, lambda w: w.setValue(5.0)),
            (QSpinBox, 13, lambda w: w.setValue(13)),
            (QLineEdit, "text", lambda w: w.setText("text")),
            (QPlainTextEdit, "hello world", lambda w: w.setPlainText("hello world")),
            (QCheckBox, True, lambda w: w.setChecked(True)),
            (QCheckBox, False, lambda w: w.setChecked(False)),
        ],
    )
    def test_get_value(
        self,
        widget_factory: Callable[[], QWidget],
        expected_value: float | int | str | bool,
        setup: Callable[[Any], None],
    ) -> None:
        widget = widget_factory()
        setup(widget)
        assert get_from_widget(widget) == expected_value

    def test_get_enum_select_combo(self) -> None:
        widget = EnumSelectCombo(enum_type=SvgGraphReadingFormat, initial_value=SvgGraphReadingFormat.katakana)
        assert get_from_widget(widget) == SvgGraphReadingFormat.katakana.name

    def test_get_qcombobox(self) -> None:
        widget = QComboBox()
        widget.addItems(["x", "y", "z"])
        widget.setCurrentIndex(2)
        assert get_from_widget(widget) == "z"

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Don't know how to handle"):
            get_from_widget(QWidget())

    def test_color_edit_picker(self) -> None:
        widget = ColorEditPicker()
        widget.set_color("#FF0000")
        assert get_from_widget(widget) == "#FF0000"

    def test_flag_select_combo(self) -> None:
        widget = FlagSelectCombo(enum_type=_TestFlags)
        widget.set_checked_flags(_TestFlags.foo | _TestFlags.bar)
        result = get_from_widget(widget)
        assert frozenset(result.split(",")) == {"foo", "bar"}

    def test_shortcut_grab_button(self) -> None:
        widget = ShortCutGrabButton(initial_value="Ctrl+G")
        assert get_from_widget(widget) == "Ctrl+G"

    def test_words_edit(self) -> None:
        widget = WordsEdit(initial_values=["word1", "word2"])
        assert get_from_widget(widget) == "word1,word2"


class TestChangeEvent:
    @pytest.mark.parametrize(
        "widget_factory",
        [
            QDoubleSpinBox,
            QSpinBox,
            QLineEdit,
            QCheckBox,
            QComboBox,
            QPlainTextEdit,
            ColorEditPicker,
            lambda: EnumSelectCombo(enum_type=SvgGraphReadingFormat),
        ],
    )
    def test_returns_signal(self, widget_factory: Callable[[], QWidget]) -> None:
        widget = widget_factory()
        event = change_event(widget)
        assert event is not None and isinstance(event, pyqtBoundSignal)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown type"):
            change_event(QWidget())


class TestAsConfigDict:
    def test_multiple_widgets(self) -> None:
        widgets = {
            "check": QCheckBox(),
            "text": QLineEdit(),
            "spin": QDoubleSpinBox(),
            "int_spin": QSpinBox(),
            "combo": QComboBox(),
            "color": ColorEditPicker(),
            "words": WordsEdit(initial_values=["a", "b"]),
        }
        widgets["combo"].addItems(["x", "y"])
        widgets["combo"].setCurrentIndex(1)
        set_from_cfg(widgets["check"], True)
        set_from_cfg(widgets["text"], "hello")
        set_from_cfg(widgets["spin"], 3.0)
        set_from_cfg(widgets["int_spin"], 7)
        widgets["color"].set_color("#00FF00")

        result = as_config_dict(widgets)
        assert result == {
            "check": True,
            "text": "hello",
            "spin": 3.0,
            "int_spin": 7,
            "combo": "y",
            "color": "#00FF00",
            "words": "a,b",
        }


class TestSvgGraphNumerics:
    def test_numerics_exclude_boolean_keys(self, no_anki_config: NoAnkiConfigView) -> None:
        numeric_keys = {item.cfg_key for item in no_anki_config.svg_graphs.numerics()}
        bool_keys = set(no_anki_config.svg_graphs.bool_keys())
        assert numeric_keys.isdisjoint(bool_keys)

    @pytest.mark.parametrize(
        "cfg_key, expected_type",
        [
            ("graph_height", int),
            ("circle_radius", float),
        ],
    )
    def test_numerics_use_default_type_metadata(
        self, no_anki_config: NoAnkiConfigView, cfg_key: str, expected_type: type[int] | type[float]
    ) -> None:
        numeric_values = {item.cfg_key: item for item in no_anki_config.svg_graphs.numerics()}
        assert isinstance(numeric_values[cfg_key].default, expected_type)
        assert isinstance(numeric_values[cfg_key].value, expected_type)


class TestSvgSettingsForm:
    @pytest.mark.parametrize(
        "widget_key, expected_type",
        [
            ("include_text", QCheckBox),
            ("color_mode", EnumSelectCombo),
            ("reading_format", EnumSelectCombo),
            ("graph_font_name", AJTPlainTextEdit),
            ("graph_horizontal_padding", PxNarrowSpinBox),
            ("size_unit", PxNarrowSpinBox),
            ("x_step", PxNarrowSpinBox),
            ("text_dx", PxNarrowSpinBox),
            ("tspan_dx", PxNarrowSpinBox),
            ("graph_height", PxNarrowSpinBox),
            ("graph_visible_height", PxNarrowSpinBox),
            ("devoiced_circle_dy", PxNarrowSpinBox),
            ("stroke_width", PxDoubleNarrowSpinBox),
            ("circle_radius", PxDoubleNarrowSpinBox),
            ("font_size", PxDoubleNarrowSpinBox),
            ("letter_spacing", PxDoubleNarrowSpinBox),
            ("devoiced_circle_width", PxDoubleNarrowSpinBox),
            ("devoiced_circle_radius", PxDoubleNarrowSpinBox),
            ("devoiced_rectangle_padding", PxDoubleNarrowSpinBox),
            ("devoiced_stroke_dasharray", StrokeDisarrayLineEdit),
            ("stroke_dasharray", StrokeDisarrayLineEdit),
        ],
    )
    def test_widget_types(
        self, no_anki_config: NoAnkiConfigView, widget_key: str, expected_type: type[QWidget]
    ) -> None:
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        widgets = form._widgets.__dict__
        assert isinstance(widgets[widget_key], expected_type)

    def test_all_widgets_have_tooltips(self, no_anki_config: NoAnkiConfigView) -> None:
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        missing_tooltips = [key for key, widget in form._widgets.__dict__.items() if not widget.toolTip()]
        assert missing_tooltips == []

    def test_graph_font_name_round_trips_through_config_dict(self, no_anki_config: NoAnkiConfigView) -> None:
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        font_name = "Noto Sans CJK JP, sans-serif"
        set_from_cfg(form._widgets.graph_font_name, font_name)

        assert as_config_dict(form._widgets.__dict__)["graph_font_name"] == font_name

    def test_graph_font_name_emits_opts_changed(self, no_anki_config: NoAnkiConfigView) -> None:
        """Changing the QPlainTextEdit font-name field emits opts_changed."""
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        font_name = "Noto Serif CJK JP, serif"
        emissions: list[None] = []
        qconnect(form.opts_changed, lambda: emissions.append(None))

        form._widgets.graph_font_name.setPlainText(font_name)

        assert emissions == [None]


class TestStrokeDisarrayLineEdit:
    @pytest.mark.parametrize(
        "text, expected_state",
        [
            ("1", QValidator.State.Acceptable),
            ("1 2", QValidator.State.Acceptable),
            ("12 34 56", QValidator.State.Acceptable),
            ("", QValidator.State.Intermediate),
            ("1 ", QValidator.State.Intermediate),
            (" 1", QValidator.State.Invalid),
            ("1  2", QValidator.State.Invalid),
            ("a", QValidator.State.Invalid),
        ],
    )
    def test_validator(self, text: str, expected_state: QValidator.State) -> None:
        """Verify Qt accepts the non-capturing dasharray regex as intended."""
        validator = StrokeDisarrayLineEdit().validator()
        assert validator is not None
        assert validator.validate(text, 0)[0] == expected_state


class TestSvgSettingsWidget:
    """SvgSettingsWidget debounces preview updates and derives its height from the config."""

    def test_debounce_timer_configured(self, no_anki_config: NoAnkiConfigView) -> None:
        """SVG preview updates are delayed by a single-shot debounce timer."""
        widget = SvgSettingsWidget(no_anki_config)

        assert widget._update_view_timer.isSingleShot() is True
        assert widget._update_view_timer.interval() == DEBOUNCE_UPDATE_VIEW_MS

    def test_form_signal_schedules_update_without_immediate_render(self, no_anki_config: NoAnkiConfigView) -> None:
        """Changing form settings starts the timer instead of reloading the web view immediately."""
        widget = SvgSettingsWidget(no_anki_config)
        font_name = "Noto Serif CJK JP, serif"
        emissions: list[None] = []
        qconnect(widget._update_view_timer.timeout, lambda: emissions.append(None))

        widget._form._widgets.graph_font_name.setPlainText(font_name)

        assert emissions == []
        assert widget._update_view_timer.isActive() is True

    def test_debounce_coalesces_rapid_changes(self, no_anki_config: NoAnkiConfigView) -> None:
        """Several rapid setting changes produce one debounced preview update."""
        widget = SvgSettingsWidget(no_anki_config)
        font_names = ("Noto Serif", "Noto Sans", "Noto Mono")
        emissions: list[None] = []
        qconnect(widget._update_view_timer.timeout, lambda: emissions.append(None))

        for font_name in font_names:
            widget._form._widgets.graph_font_name.setPlainText(font_name)
        QTest.qWait(DEBOUNCE_UPDATE_VIEW_MS + 50)

        assert emissions == [None]
        assert widget._cfg_clone.svg_graphs.graph_font_name == font_names[-1]

    def test_preview_changes_do_not_mutate_original_config(self, no_anki_config: NoAnkiConfigView) -> None:
        """Preview updates use a config clone until the settings dialog accepts changes."""
        include_text = False
        original_include_text = no_anki_config.svg_graphs.include_text
        widget = SvgSettingsWidget(no_anki_config)

        widget._form._widgets.include_text.setChecked(include_text)
        widget.update_view()

        assert widget._cfg_clone.svg_graphs.include_text is include_text
        assert no_anki_config.svg_graphs.include_text is original_include_text

    def test_preview_webview_minimum_height_matches_graph_visible_height(
        self, no_anki_config: NoAnkiConfigView
    ) -> None:
        """The preview webview reserves enough vertical space for the configured graph height."""
        widget = SvgSettingsWidget(no_anki_config)

        assert widget._web_view.minimumHeight() == (
            widget._cfg_clone.svg_graphs.graph_visible_height + SVG_SETTINGS_BODY_VERTICAL_PADDING
        )

    def test_preview_webview_size_policy_prefers_vertical_expansion(self, no_anki_config: NoAnkiConfigView) -> None:
        """The preview webview expands vertically before the settings forms consume extra space."""
        widget = SvgSettingsWidget(no_anki_config)

        assert widget._web_view.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        assert widget._web_view.sizePolicy().verticalPolicy() == QSizePolicy.Policy.MinimumExpanding
