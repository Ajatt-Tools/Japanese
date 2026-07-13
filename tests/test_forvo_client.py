# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest
from bs4 import BeautifulSoup, Tag

from japanese.audio_manager.forvo_client import audio_transcription_from_play_button


def make_button(text: str) -> Tag:
    """Return a BeautifulSoup tag that mimics a Forvo play button."""
    button = BeautifulSoup(f"<button>{text}</button>", "html.parser").button
    assert isinstance(button, Tag)
    return button


class TestAudioTranscriptionFromPlayButton:
    @pytest.mark.parametrize(
        "button_text, expected",
        [
            ("東京 pronunciation", "東京"),
            ("hello   world pronunciation", "hello_world"),
            ("  spaced\nword\tpronunciation  ", "spaced_word"),
        ],
    )
    def test_normalizes_whitespace(self, button_text: str, expected: str) -> None:
        """Whitespace in Forvo button text is normalized to filename-safe underscores."""
        assert audio_transcription_from_play_button(make_button(button_text)) == expected
