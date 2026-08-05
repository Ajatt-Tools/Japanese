# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import typing

import pytest
from bs4 import BeautifulSoup, Tag

from japanese.audio_manager.forvo_client import (
    ForvoClient,
    ForvoConfig,
    ForvoPronunciation,
    audio_transcription_from_play_button,
)


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


def make_pronunciation(username: str, country: str | None) -> ForvoPronunciation:
    """Return a minimal Forvo pronunciation with the given username and country."""
    return ForvoPronunciation(word="東京", username=username, audio_url="https://example.com/a.mp3", country=country)


class SortScenario(typing.NamedTuple):
    """A sort_pronunciations scenario: input pronunciations and the expected username order."""

    pronunciations: list[ForvoPronunciation]
    expected_usernames: list[str]


class TestSortPronunciations:
    """sort_pronunciations orders by preferred usernames, then preferred countries."""

    CONFIG = ForvoConfig(preferred_countries=["japan"])

    SCENARIOS: typing.Final[dict[str, SortScenario]] = {
        # Preferred country comes first; unpreferred and missing countries go last, stably.
        "none_country_sorted_last": SortScenario(
            pronunciations=[
                make_pronunciation("user_no_country", None),
                make_pronunciation("user_japan", "Japan"),
                make_pronunciation("user_germany", "Germany"),
            ],
            expected_usernames=["user_japan", "user_no_country", "user_germany"],
        ),
        # All countries missing: the order is preserved (no AttributeError on None.lower()).
        "all_countries_none": SortScenario(
            pronunciations=[
                make_pronunciation("user_a", None),
                make_pronunciation("user_b", None),
            ],
            expected_usernames=["user_a", "user_b"],
        ),
    }

    @pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=list(SCENARIOS.keys()))
    def test_sort_pronunciations(self, scenario: SortScenario) -> None:
        """Pronunciations with None country are treated as unpreferred, never crash."""
        client = ForvoClient(self.CONFIG)
        assert [p.username for p in client.sort_pronunciations(scenario.pronunciations)] == scenario.expected_usernames
