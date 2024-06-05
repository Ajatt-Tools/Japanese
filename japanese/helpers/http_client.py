# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Optional, Protocol, Union

import anki.httpclient
import requests
from requests import RequestException

try:
    from .misc import clamp
except ImportError:
    from misc import clamp


@dataclasses.dataclass(frozen=True)
class FileUrlData:
    url: str
    desired_filename: str
    word: str
    source_name: str
    reading: str = ""
    pitch_number: str = "?"


@dataclasses.dataclass
class AudioSourceConfig:
    enabled: bool
    name: str
    url: str

    @property
    def is_valid(self) -> str:
        return self.name and self.url


@dataclasses.dataclass
class AudioManagerException(RequestException):
    file: Union[AudioSourceConfig, FileUrlData]
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None

    def describe_short(self) -> str:
        return str(self.exception.__class__.__name__ if self.exception else self.response.status_code)


class AudioSettingsProtocol(Protocol):
    dictionary_download_timeout: int
    audio_download_timeout: int
    attempts: int


class AudioManagerHttpClient:
    # add some fake headers to convince sites we're not a bot.
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "TE": "trailers",
    }

    def __init__(
        self,
        audio_settings: AudioSettingsProtocol,
        progress_hook: Optional[anki.httpclient.ProgressCallback] = None,
    ) -> None:
        self._audio_settings = audio_settings
        self._client = anki.httpclient.HttpClient(progress_hook)

    def _get_with_timeout(self, url: str, timeout: int) -> requests.Response:
        # Set timeout
        self._client.timeout = clamp(min_val=2, val=timeout, max_val=99)
        return self._client.get(url, headers=self.headers.copy())

    def _get_with_retry(self, url: str, timeout: int, attempts: int) -> requests.Response:
        for _attempt in range(clamp(min_val=0, val=attempts - 1, max_val=99)):
            try:
                return self._get_with_timeout(url, timeout)
            except requests.Timeout:
                continue
        # If other tries timed out.
        return self._get_with_timeout(url, timeout)

    def download(self, file: Union[AudioSourceConfig, FileUrlData]) -> bytes:
        """
        Get an audio source or audio file.
        """
        timeout = (
            self._audio_settings.dictionary_download_timeout
            if isinstance(file, AudioSourceConfig)
            else self._audio_settings.audio_download_timeout
        )
        attempts = self._audio_settings.attempts

        try:
            response = self._get_with_retry(file.url, timeout, attempts)
        except OSError as ex:
            raise AudioManagerException(
                file,
                f"{file.url} download failed with {ex.__class__.__name__}",
                exception=ex,
            )
        if response.status_code != requests.codes.ok:
            raise AudioManagerException(
                file,
                f"{file.url} download failed with return code {response.status_code}",
                response=response,
            )
        return self._client.stream_content(response)
