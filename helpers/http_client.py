# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Optional, Union, Protocol

import anki.httpclient
import requests
from requests import RequestException


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
        return str(
            self.exception.__class__.__name__
            if self.exception
            else
            self.response.status_code
        )


class AudioSettingsProtocol(Protocol):
    dictionary_download_timeout: int
    audio_download_timeout: int
    attempts: int


class AudioManagerHttpClient(anki.httpclient.HttpClient):
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
            progress_hook: Optional[anki.httpclient.ProgressCallback] = None
    ) -> None:
        super().__init__(progress_hook)
        self._audio_settings = audio_settings

    def get(self, url: str, headers: dict[str, str] = None):
        # Mask the default get function in case it is called by mistake.
        raise NotImplementedError()

    def _get_with_timeout(self, url: str, timeout: int) -> requests.Response:
        # Set headers
        headers = self.headers.copy()
        headers["User-Agent"] = self._agent_name()

        # Set timeout
        timeout = timeout or self.timeout

        return self.session.get(
            url, stream=True, headers=headers, timeout=timeout, verify=self.verify
        )

    def _get_with_retry(self, url: str, timeout: int, attempts: int) -> requests.Response:
        for _attempt in range(min(max(0, attempts - 1), 99)):
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
                f'{file.url} download failed with {ex.__class__.__name__}',
                exception=ex
            )
        if response.status_code != requests.codes.ok:
            raise AudioManagerException(
                file,
                f'{file.url} download failed with return code {response.status_code}',
                response=response
            )
        return self.stream_content(response)


def main():
    class AudioSettings:
        dictionary_download_timeout = 10
        audio_download_timeout = 10
        attempts = 10

    client = AudioManagerHttpClient(audio_settings=AudioSettings())
    try:
        client.download(FileUrlData(url="x", word="x", desired_filename="x", source_name="x"))
    except AudioManagerException:
        print("Done.")


if __name__ == "__main__":
    main()
