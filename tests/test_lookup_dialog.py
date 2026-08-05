# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib
import typing
from collections.abc import Callable

import pytest

from japanese.lookup_dialog import ViewPitchAccentsDialog
from japanese.pitch_accents.acc_dict_mgr_2 import AccentDictManager2
from japanese.widgets.raise_on_show_dialog import RaiseOnShowDialog
from japanese.widgets.webview import NoAnkiSVGPreviewWebView
from playground.utils import NoAnkiConfigView
from tests.conftest import (
    acc_dict_mgr,
    tmp_sqlite3_db_path,
)
from tests.helpers import make_accent_lookup

# 僕 has 5 unique pitch notations in the bundled data
# (ボク:0, ボク:1, シモベ:0, シモベ:3, ヤツガレ:0).
EXPECTED_BOKU_NOTATIONS: typing.Final[int] = 5


class RecordingRaiseOnShowDialog(RaiseOnShowDialog):
    """RaiseOnShowDialog variant that records raise_ calls."""

    name: str = "ajt__recording_raise_on_show_dialog"

    def __init__(self) -> None:
        """Initialize the dialog with a raise-call counter."""
        super().__init__()
        self.raise_count = 0

    def raise_(self) -> None:
        """Record that show() requested the dialog to be raised."""
        self.raise_count += 1


class OutsideAnkiScenario(typing.NamedTuple):
    """An operation that must fail outside Anki because an Anki-only global is unavailable."""

    operation: Callable[[NoAnkiConfigView], object]


OUTSIDE_ANKI_SCENARIOS: dict[str, OutsideAnkiScenario] = {
    # Without an injected AccentLookup, the dialog would need the Anki-only global factory.
    "construction_without_accent_lookup": OutsideAnkiScenario(
        operation=lambda cfg: ViewPitchAccentsDialog(cfg),
    ),
    # Without an accent database path, lookups would need the Anki-only global path.
    "lookup_without_accent_db_path": OutsideAnkiScenario(
        operation=lambda cfg: ViewPitchAccentsDialog(cfg, accent_lookup=make_accent_lookup(cfg)).lookup_pronunciations(
            "僕"
        ),
    ),
}


class TestOutsideAnkiRequirements:
    """Outside Anki, the dialog refuses to fall back to Anki-only globals."""

    @pytest.mark.parametrize("scenario", OUTSIDE_ANKI_SCENARIOS.values(), ids=list(OUTSIDE_ANKI_SCENARIOS.keys()))
    def test_missing_dependency_raises(self, no_anki_config: NoAnkiConfigView, scenario: OutsideAnkiScenario) -> None:
        """Each operation raises AssertionError when its explicit dependency is absent."""
        with pytest.raises(AssertionError):
            scenario.operation(no_anki_config)


class TestViewPitchAccentsDialog:
    """Dialog behavior with a real (temporary) pitch accent database."""

    @pytest.fixture(scope="class")
    @classmethod
    def dialog(
        cls,
        no_anki_config: NoAnkiConfigView,
        tmp_sqlite3_db_path: pathlib.Path,
        acc_dict_mgr: AccentDictManager2,
    ) -> ViewPitchAccentsDialog:
        """Create the dialog with an injected AccentLookup and temporary database."""
        return ViewPitchAccentsDialog(
            no_anki_config,
            accent_lookup=make_accent_lookup(no_anki_config),
            accent_db_path=tmp_sqlite3_db_path,
        )

    def test_dialog_is_raise_on_show(self, dialog: ViewPitchAccentsDialog) -> None:
        """The persistent dialog raises above other windows when shown."""
        assert isinstance(dialog, RaiseOnShowDialog)

    def test_raise_on_show_calls_raise(self) -> None:
        """RaiseOnShowDialog.show calls raise_ even when the dialog is already reusable."""
        dialog = RecordingRaiseOnShowDialog()
        dialog.show()

        assert dialog.raise_count == 1
        dialog.hide()

    def test_webview_is_no_anki(self, dialog: ViewPitchAccentsDialog) -> None:
        """Outside Anki, the standalone web view with inlined CSS is selected."""
        assert isinstance(dialog._web, NoAnkiSVGPreviewWebView)

    def test_svg_maker_is_shared_with_formatter(self, dialog: ViewPitchAccentsDialog) -> None:
        """The dialog and its formatter share one SVG adapter instance."""
        assert dialog._formatter._svg_maker is dialog._svg_maker

    def test_lookup_pronunciations(self, dialog: ViewPitchAccentsDialog) -> None:
        """A real lookup returns pronunciations grouped by headword."""
        dialog.lookup_pronunciations("僕")
        assert list(dialog._pronunciations.keys()) == ["僕"]

    @pytest.mark.parametrize(
        "marker",
        [
            '<div class="keyword"><ul>',
            "<li>僕</li>",
            '<div class="pitch_accents">',
            '<svg class="ajt__pitch_svg"',
        ],
    )
    def test_format_html_result_after_lookup(self, dialog: ViewPitchAccentsDialog, marker: str) -> None:
        """The rendered HTML repeats each block once per unique pitch notation."""
        dialog.lookup_pronunciations("僕")
        assert dialog._format_html_result().count(marker) == EXPECTED_BOKU_NOTATIONS

    def test_show_smoke(self, dialog: ViewPitchAccentsDialog) -> None:
        """Showing the persistent dialog works outside Anki (offscreen)."""
        dialog.show()
        assert dialog.isVisible() is True
        dialog.hide()
