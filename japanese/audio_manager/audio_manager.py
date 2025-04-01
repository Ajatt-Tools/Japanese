# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import pathlib
from typing import Optional

from aqt import mw

from ..config_view import JapaneseConfig
from ..helpers.basic_types import AudioManagerHttpClientABC
from ..helpers.http_client import AudioManagerHttpClient


class AudioSourceManagerFactory:
    _config: JapaneseConfig
    _http_client: AudioManagerHttpClientABC
    _db_path: Optional[pathlib.Path] = None

    def __new__(cls, *args, **kwargs):
        try:
            obj = cls._instance  # type: ignore
        except AttributeError:
            obj = cls._instance = super().__new__(cls)
        return obj

    def __init__(self, config: JapaneseConfig, db_path: Optional[pathlib.Path] = None) -> None:
        self._config = config
        self._db_path = db_path or self._db_path
        self._http_client = AudioManagerHttpClient(self._config.audio_settings)
        if mw:
            assert self._db_path is None
