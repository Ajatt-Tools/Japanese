# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from unittest.mock import create_autospec

import pytest
from aqt.editor import Editor

from japanese.context_menu import RemoveSpaces
from japanese.furigana.gen_furigana import FuriganaGen
from tests.helpers import make_fresh_config


def make_editor_mock() -> Editor:
    """Return an editor mock with the web attribute used by ContextMenuAction."""
    editor = create_autospec(Editor, instance=True)
    editor.web = object()
    return editor


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
