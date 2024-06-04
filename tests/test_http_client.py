# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pytest

from japanese.helpers.http_client import AudioManagerHttpClient, FileUrlData, AudioManagerException


def test_client_download() -> None:
    class AudioSettings:
        dictionary_download_timeout = 10
        audio_download_timeout = 10
        attempts = 10

    client = AudioManagerHttpClient(audio_settings=AudioSettings())

    with pytest.raises(AudioManagerException):
        client.download(FileUrlData(url="x", word="x", desired_filename="x", source_name="x"))
