# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import io
import os
from typing import Any, Optional, Union

import anki.httpclient
import requests

from ..ajt_common.utils import clamp
from ..audio_manager.abstract import AudioSettingsConfigViewABC
from ..audio_manager.basic_types import (
    AudioManagerException,
    AudioSourceConfig,
    FileUrlData,
)
from .basic_types import AudioManagerHttpClientABC


def get_headers() -> dict[str, str]:
    """
    Use some fake headers to convince sites we're not a bot.
    """
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "TE": "trailers",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
    }


class AjtHttpClient:
    """
    Http Client adapted from Anki with minor tweaks.
    https://github.com/ankitects/anki/blob/a6d5c949970627f2b4dcea8a02fea3a497e0440f/pylib/anki/httpclient.py
    """

    verify = True
    # args are (upload_bytes_in_chunk, download_bytes_in_chunk)
    progress_hook: Optional[anki.httpclient.ProgressCallback] = None

    def __init__(self, progress_hook: Optional[anki.httpclient.ProgressCallback] = None) -> None:
        self.progress_hook = progress_hook
        self.session = requests.Session()
        if os.environ.get("ANKI_NOVERIFYSSL"):
            # allow user to accept invalid certs in work/school settings
            self.verify = False

    def __enter__(self) -> "AjtHttpClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        if self.session:
            self.session.close()
            self.session = None

    def __del__(self) -> None:
        self.close()

    def post(self, url: str, data: bytes, timeout: Optional[int] = None) -> requests.Response:
        return self.session.post(
            url,
            data=data,
            headers=get_headers(),
            stream=True,
            timeout=timeout,
            verify=self.verify,
        )

    def get_with_timeout(self, url: str, timeout: Optional[int] = None) -> requests.Response:
        return self.session.get(
            url,
            stream=True,
            headers=get_headers(),
            timeout=clamp(min_val=2, val=timeout, max_val=99),
            verify=self.verify,
        )

    def stream_content(self, resp: requests.Response) -> bytes:
        resp.raise_for_status()
        buf = io.BytesIO()
        for chunk in resp.iter_content(chunk_size=anki.httpclient.HTTP_BUF_SIZE):
            if self.progress_hook:
                self.progress_hook(0, len(chunk))
            buf.write(chunk)
        return buf.getvalue()

    def get_with_retry(self, url: str, timeout: int, attempts: int) -> requests.Response:
        for _attempt in range(clamp(min_val=0, val=attempts - 1, max_val=99)):
            try:
                return self.get_with_timeout(url, timeout=timeout)
            except requests.Timeout:
                print(f"timeout: {url}")
                continue
        # If other tries timed out.
        return self.get_with_timeout(url, timeout)


class AudioManagerHttpClient(AudioManagerHttpClientABC):
    def __init__(
        self,
        audio_settings: AudioSettingsConfigViewABC,
        progress_hook: Optional[anki.httpclient.ProgressCallback] = None,
    ) -> None:
        self._audio_settings = audio_settings
        self._client = AjtHttpClient(progress_hook)

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
            response = self._client.get_with_retry(file.url, timeout, attempts)
        except OSError as ex:
            raise AudioManagerException(
                file,
                f"{file.url} download failed with exception {ex.__class__.__name__}",
                exception=ex,
            )
        if response.status_code != requests.codes.ok:
            raise AudioManagerException(
                file,
                f"{file.url} download failed with return code {response.status_code}",
                response=response,
            )
        return self._client.stream_content(response)
