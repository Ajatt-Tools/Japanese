# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import typing
from typing import Optional, Union

import requests

from ..helpers.types import SourceConfig, SourceConfigDict
from ..pitch_accents.consts import NO_ACCENT


@dataclasses.dataclass(frozen=True)
class FileUrlData:
    url: str
    desired_filename: str
    word: str
    source_name: str
    reading: str = ""
    pitch_number: str = NO_ACCENT


class AudioSourceConfigDict(SourceConfigDict):
    pass


@dataclasses.dataclass
class AudioSourceConfig(SourceConfig):
    pass


class AudioManagerExceptionBase(OSError):
    response: Optional[requests.Response]
    exception: Optional[Exception]

    def describe_short(self) -> str:
        if self.exception is None and self.response is None:
            raise ValueError("can't produce a short description. no response or exception provided.")
        return str(self.exception.__class__.__name__ if self.exception else self.response.status_code)


@dataclasses.dataclass
class AudioManagerException(AudioManagerExceptionBase):
    file: Union[AudioSourceConfig, FileUrlData]
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None


class NameUrl(typing.NamedTuple):
    name: str
    url: str


class NameUrlSet(frozenset[NameUrl]):
    """This type is created to work around pyqtSignal not accepting generic types."""

    pass


@dataclasses.dataclass(frozen=True)
class AudioStats:
    source_name: str
    num_files: int
    num_headwords: int


@dataclasses.dataclass(frozen=True)
class TotalAudioStats:
    unique_headwords: int
    unique_files: int
    sources: list[AudioStats]
