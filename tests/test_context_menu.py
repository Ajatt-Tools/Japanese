# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from unittest.mock import create_autospec

import pytest
from aqt.editor import Editor
from aqt.webview import AnkiWebView

import japanese.context_menu as context_menu
from japanese.context_menu import ContextMenuAction, RemoveSpaces
from japanese.furigana.gen_furigana import FuriganaGen
from tests.helpers import make_fresh_config


def make_editor_mock() -> Editor:
    """Return an editor mock with the web attribute used by ContextMenuAction."""
    editor = create_autospec(Editor, instance=True)
    editor.web = create_autospec(AnkiWebView, instance=True)
    return editor


def make_new_editor_mock() -> Editor:
    """Return an Editor-like mock that lacks doPaste, like Anki's new editor."""
    editor = make_editor_mock()
    del editor.doPaste
    return editor


class RaisesAttributeError(ContextMenuAction):
    """Context menu action that raises AttributeError before paste is attempted."""

    key = "remove_spaces"
    label = "Raises AttributeError"

    def action(self, text: str) -> str:
        """Raise AttributeError from action code, not from editor.doPaste."""
        raise AttributeError("action failed")


ContextMenuAction.subclasses.remove(RaisesAttributeError)


class TestRemoveSpaces:
    """RemoveSpaces strips whitespace and pastes the result, including empty strings."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("   ", ""),
            ("a b c", "abc"),
            ("abc", "abc"),
            ("  hello  world  ", "helloworld"),
        ],
    )
    def test_action_strips_spaces(self, text: str, expected: str) -> None:
        """action() removes all whitespace from the input."""
        action = RemoveSpaces(
            make_fresh_config(),
            fgen=create_autospec(FuriganaGen, instance=True),
            editor=make_editor_mock(),
        )

        assert action.action(text) == expected

    @pytest.mark.parametrize(
        ("selected_text", "expected_paste"),
        [
            ("   ", ""),
            ("a b c", "abc"),
            ("abc", "abc"),
        ],
    )
    def test_try_paste_text_calls_do_paste(self, selected_text: str, expected_paste: str) -> None:
        """_try_paste_text calls editor.doPaste even when the result is an empty string."""
        editor = make_editor_mock()
        action = RemoveSpaces(
            make_fresh_config(),
            fgen=create_autospec(FuriganaGen, instance=True),
            editor=editor,
        )

        action._try_paste_text(selected_text)

        editor.doPaste.assert_called_once_with(expected_paste, internal=True, extended=False)

    def test_try_paste_text_warns_when_new_editor_has_no_do_paste(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_try_paste_text shows a warning when Anki's new editor has no paste API."""
        warnings: list[str] = []
        monkeypatch.setattr(context_menu, "show_warning", warnings.append)
        action = RemoveSpaces(
            make_fresh_config(),
            fgen=create_autospec(FuriganaGen, instance=True),
            editor=make_new_editor_mock(),
        )

        action._try_paste_text("a b c")

        assert "".join(warnings).startswith(context_menu.NEW_EDITOR_PASTE_UNSUPPORTED)

    def test_init_requires_editor_or_webview(self) -> None:
        """Context menu actions fail early when neither webview nor editor is provided."""
        with pytest.raises(ValueError, match="webview or editor must be provided"):
            RemoveSpaces(make_fresh_config(), fgen=create_autospec(FuriganaGen, instance=True))

    def test_action_attribute_error_is_not_reported_as_editor_paste_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AttributeError from action() propagates instead of becoming a new-editor warning."""
        warnings: list[str] = []
        monkeypatch.setattr(context_menu, "show_warning", warnings.append)
        action = RaisesAttributeError(
            make_fresh_config(),
            fgen=create_autospec(FuriganaGen, instance=True),
            editor=make_editor_mock(),
        )

        with pytest.raises(AttributeError, match="action failed"):
            action._try_paste_text("a b c")

        assert warnings == []
