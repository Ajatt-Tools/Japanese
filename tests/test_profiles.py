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


def test_read_profiles(no_anki_config) -> None:
    profiles = [*no_anki_config.iter_profiles()]
    assert len(profiles) > 0


def test_create_profile_furigana(furigana_dict) -> None:
    profile = Profile.from_config_dict(furigana_dict)
    assert isinstance(profile, ProfileFurigana)
    assert profile.mode == "furigana"
    assert profile.source == "SentKanji"
    assert profile.destination == "SentFurigana"


def test_create_profile_pitch(pitch_dict) -> None:
    profile = Profile.from_config_dict(pitch_dict)
    assert isinstance(profile, ProfilePitch)
    assert profile.mode == "pitch"
    assert profile.source == "VocabKanji"
    assert profile.destination == "VocabPitchPattern"


def test_create_profile_audio(audio_dict) -> None:
    profile = Profile.from_config_dict(audio_dict)
    assert isinstance(profile, ProfileAudio)
    assert profile.mode == "audio"
    assert profile.source == "VocabKanji"
    assert profile.destination == "VocabAudio"
