# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from collections.abc import Callable

import pytest
from aqt.qt import QCheckBox, QDoubleSpinBox, QLineEdit, QWidget

from japanese.widgets.widgets_to_config_dict import (
    as_config_dict,
    change_event,
    get_from_widget,
    set_from_cfg,
)


class TestSetFromCfg:
    @pytest.mark.parametrize(
        "widget_factory, value",
        [
            (QDoubleSpinBox, 42.0),
            (QLineEdit, "hello"),
            (QCheckBox, True),
            (QCheckBox, False),
        ],
    )
    def test_set_value(self, widget_factory: type[QWidget], value: float | str | bool) -> None:
        widget = widget_factory()
        set_from_cfg(widget, value)
        assert get_from_widget(widget) == value

    def test_unknown_type_raises(self) -> None:
        widget = QWidget()
        with pytest.raises(ValueError, match="Can't handle widget"):
            set_from_cfg(widget, 42)


class TestGetFromWidget:
    @pytest.mark.parametrize(
        "widget_factory, expected_value, setup",
        [
            (QDoubleSpinBox, 5.0, lambda w: w.setValue(5.0)),
            (QLineEdit, "text", lambda w: w.setText("text")),
            (QCheckBox, True, lambda w: w.setChecked(True)),
            (QCheckBox, False, lambda w: w.setChecked(False)),
        ],
    )
    def test_get_value(
        self,
        widget_factory: type[QWidget],
        expected_value: float | str | bool,
        setup: Callable[[QWidget], None],
    ) -> None:
        widget = widget_factory()
        setup(widget)
        assert get_from_widget(widget) == expected_value

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Don't know how to handle"):
            get_from_widget(QWidget())


class TestChangeEvent:
    @pytest.mark.parametrize(
        "widget_factory",
        [QDoubleSpinBox, QLineEdit, QCheckBox],
    )
    def test_returns_signal(self, widget_factory: type[QWidget]) -> None:
        widget = widget_factory()
        assert change_event(widget) is not None

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown type"):
            change_event(QWidget())


class TestAsConfigDict:
    def test_multiple_widgets(self) -> None:
        widgets = {
            "check": QCheckBox(),
            "text": QLineEdit(),
            "spin": QDoubleSpinBox(),
        }
        set_from_cfg(widgets["check"], True)
        set_from_cfg(widgets["text"], "hello")
        set_from_cfg(widgets["spin"], 3.0)

        assert as_config_dict(widgets) == {"check": True, "text": "hello", "spin": 3.0}
