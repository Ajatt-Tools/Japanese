# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pytest

from japanese.helpers.profiles import (
    ColorCodePitchFormat,
    Profile,
    ProfileAudio,
    ProfileFurigana,
    ProfilePitch,
    TaskCaller,
    TaskCallerOpts,
    flag_as_comma_separated_list,
    flag_from_comma_separated_list,
)
from tests.no_anki_config import no_anki_config


@pytest.fixture(scope="session")
def furigana_dict() -> dict[str, object]:
    return {
        "name": "Add furigana for sentence",
        "note_type": "japanese",
        "source": "Expression",
        "destination": "ExpressionFurigana",
        "mode": "furigana",
        "split_morphemes": True,
        "triggered_by": "focus_lost,toolbar_button,note_added,bulk_add",
        "overwrite_destination": False,
        "color_code_pitch": "color",
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
        "triggered_by": "focus_lost,bulk_add",
        "overwrite_destination": False,
    }


def test_read_profiles(no_anki_config) -> None:
    profiles = [*no_anki_config.iter_profiles()]
    assert len(profiles) > 0


def test_create_profile_furigana(furigana_dict) -> None:
    for idx in range(2):
        profile = Profile.from_config_dict(furigana_dict)
        assert isinstance(profile, ProfileFurigana)
        assert profile.mode == "furigana"
        assert profile.source == "Expression"
        assert profile.destination == "ExpressionFurigana"
        assert profile.color_code_pitch == ColorCodePitchFormat.color
        assert profile.triggered_by == TaskCaller.all_enabled()


def test_create_profile_pitch(pitch_dict) -> None:
    profile = Profile.from_config_dict(pitch_dict)
    assert isinstance(profile, ProfilePitch)
    assert profile.mode == "pitch"
    assert profile.source == "VocabKanji"
    assert profile.destination == "VocabPitchPattern"
    assert profile.triggered_by == TaskCaller.all_enabled()


def test_create_profile_audio(audio_dict) -> None:
    profile = Profile.from_config_dict(audio_dict)
    assert isinstance(profile, ProfileAudio)
    assert profile.mode == "audio"
    assert profile.source == "VocabKanji"
    assert profile.destination == "VocabAudio"
    assert profile.triggered_by == TaskCaller.focus_lost | TaskCaller.bulk_add


def test_flag_as_comma_separated_list() -> None:
    ccpf = ColorCodePitchFormat
    assert flag_as_comma_separated_list(ccpf.attributes | ccpf.underline) == "attributes,underline"
    assert flag_as_comma_separated_list(ccpf.attributes | ccpf.color) == "attributes,color"
    assert flag_as_comma_separated_list(ccpf.color | ccpf.attributes) == "attributes,color"
    assert flag_as_comma_separated_list(ccpf.color | ccpf.attributes | ccpf.underline) == "attributes,color,underline"
    assert flag_as_comma_separated_list(ccpf(0) | ccpf.color) == "color"
    assert flag_as_comma_separated_list(ccpf(0)) == ""


def test_flag_from_comma_separated_list() -> None:
    ccpf = ColorCodePitchFormat
    get_flg = flag_from_comma_separated_list
    assert get_flg(ccpf, "") == ccpf(0)
    assert get_flg(ccpf, "color") == ccpf.color
    assert get_flg(ccpf, "underline") == ccpf.underline
    assert get_flg(ccpf, "color,attributes") == ccpf.color | ccpf.attributes
    assert get_flg(ccpf, "color,attributes,underline") == ccpf.color | ccpf.attributes | ccpf.underline
    assert get_flg(ccpf, "missing") == ccpf(0)


def test_task_callers() -> None:
    tc = TaskCaller
    assert tc.all_enabled() == tc.focus_lost | tc.toolbar_button | tc.note_added | tc.bulk_add
    assert tc.bulk_add.cfg == TaskCallerOpts(audio_download_report=False)
    assert tc.focus_lost.cfg == TaskCallerOpts(audio_download_report=True)
