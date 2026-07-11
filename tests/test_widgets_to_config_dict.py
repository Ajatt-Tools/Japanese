# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum

import pytest
from aqt.qt import *

from japanese.ajt_common.color_picker import ColorEditPicker
from japanese.ajt_common.enum_select_combo import EnumSelectCombo
from japanese.ajt_common.grab_key import ShortCutGrabButton
from japanese.config_view import SvgGraphReadingFormat
from japanese.widgets.addon_opts import (
    AJTPlainTextEdit,
    NarrowLineEdit,
    PxDoubleNarrowSpinBox,
    PxNarrowSpinBox,
    StrokeDisarrayLineEdit,
    WordsEdit,
)
from japanese.widgets.enum_selector import FlagSelectCombo
from japanese.widgets.settings_form import SvgSettingsForm
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
            (QCheckBox, True),
            (QCheckBox, False),
        ],
    )
    def test_set_value(self, widget_factory: type[QWidget], value: float | int | str | bool) -> None:
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

    def test_set_plain_text_edit(self) -> None:
        widget = QPlainTextEdit()
        set_from_cfg(widget, "Noto Sans")
        assert get_from_widget(widget) == "Noto Sans"

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
            (QCheckBox, True, lambda w: w.setChecked(True)),
            (QCheckBox, False, lambda w: w.setChecked(False)),
        ],
    )
    def test_get_value(
        self,
        widget_factory: type[QWidget],
        expected_value: float | int | str | bool,
        setup: Callable[[QWidget], None],
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

    def test_plain_text_edit(self) -> None:
        widget = QPlainTextEdit()
        widget.setPlainText("hello world")
        assert get_from_widget(widget) == "hello world"


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
            lambda: EnumSelectCombo(enum_type=SvgGraphReadingFormat),
        ],
    )
    def test_returns_signal(self, widget_factory: type[QWidget]) -> None:
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

    def test_numerics_use_default_type_metadata(self, no_anki_config: NoAnkiConfigView) -> None:
        numeric_values = {item.cfg_key: item for item in no_anki_config.svg_graphs.numerics()}
        assert isinstance(numeric_values["graph_height"].default, int)
        assert isinstance(numeric_values["graph_height"].value, int)
        assert isinstance(numeric_values["circle_radius"].default, float)
        assert isinstance(numeric_values["circle_radius"].value, float)


class TestSvgSettingsForm:
    def test_widget_types(self, no_anki_config: NoAnkiConfigView) -> None:
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        widgets = form._widgets.__dict__

        assert isinstance(widgets["include_text"], QCheckBox)
        assert isinstance(widgets["inject_css_into_files"], QCheckBox)
        assert isinstance(widgets["reading_format"], EnumSelectCombo)
        assert isinstance(widgets["graph_font_name"], AJTPlainTextEdit)

        for key in (
            "graph_horizontal_padding",
            "size_unit",
            "x_step",
            "text_dx",
            "tspan_dx",
            "graph_height",
            "graph_visible_height",
            "devoiced_circle_dy",
        ):
            assert isinstance(widgets[key], PxNarrowSpinBox)

        for key in (
            "stroke_width",
            "circle_radius",
            "font_size",
            "letter_spacing",
            "devoiced_circle_width",
            "devoiced_circle_radius",
            "devoiced_rectangle_padding",
        ):
            assert isinstance(widgets[key], PxDoubleNarrowSpinBox)

        assert isinstance(widgets["devoiced_stroke_dasharray"], StrokeDisarrayLineEdit)
        assert isinstance(widgets["stroke_dasharray"], StrokeDisarrayLineEdit)

    def test_all_widgets_have_tooltips(self, no_anki_config: NoAnkiConfigView) -> None:
        form = SvgSettingsForm(config=no_anki_config.svg_graphs)
        missing_tooltips = [key for key, widget in form._widgets.__dict__.items() if not widget.toolTip()]
        assert missing_tooltips == []
