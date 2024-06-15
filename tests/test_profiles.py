# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.profiles import (
    Profile,
    ProfileAudio,
    ProfileFurigana,
    ProfilePitch,
)
from tests.no_anki_config import no_anki_config


@pytest.fixture(scope="session")
def furigana_dict() -> dict[str, object]:
    return {
        "name": "Add furigana for sentence",
        "note_type": "japanese",
        "source": "SentKanji",
        "destination": "SentFurigana",
        "mode": "furigana",
        "split_morphemes": True,
        "triggered_by": "focus_lost,toolbar_button,note_added,bulk_add",
        "overwrite_destination": False,
        "color_code_pitch": "none",
    }


@pytest.fixture(scope="session")
def pitch_dict() -> dict[str, object]:
    return {
        "name": "Add pitch accent for word",
        "note_type": "japanese",
        "source": "VocabKanji",
        "destination": "VocabPitchPattern",
        "mode": "pitch",
        "split_morphemes": False,
        "output_format": "html_and_number",
        "triggered_by": "focus_lost,toolbar_button,note_added,bulk_add",
        "overwrite_destination": False,
    }


@pytest.fixture(scope="session")
def audio_dict() -> dict[str, object]:
    return {
        "name": "Add audio for word",
        "note_type": "Japanese",
        "source": "VocabKanji",
        "destination": "VocabAudio",
        "mode": "audio",
        "split_morphemes": False,
        "triggered_by": "focus_lost,toolbar_button,note_added,bulk_add",
        "overwrite_destination": False,
    }


def test_read_profiles(no_anki_config):
    profiles = [*no_anki_config.iter_profiles()]
    assert len(profiles) > 0


def test_create_profile(furigana_dict, pitch_dict, audio_dict):
    profile = Profile(**furigana_dict)
    assert isinstance(profile, ProfileFurigana)
    profile = Profile(**pitch_dict)
    assert isinstance(profile, ProfilePitch)
    profile = Profile(**audio_dict)
    assert isinstance(profile, ProfileAudio)
