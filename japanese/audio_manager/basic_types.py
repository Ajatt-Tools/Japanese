# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import typing
from typing import Optional, Union

import requests
from requests import RequestException

from ..helpers.types import SourceConfig, SourceConfigDict


@dataclasses.dataclass(frozen=True)
class FileUrlData:
    url: str
    desired_filename: str
    word: str
    source_name: str
    reading: str = ""
    pitch_number: str = "?"


class AudioSourceConfigDict(SourceConfigDict):
    pass


@dataclasses.dataclass
class AudioSourceConfig(SourceConfig):
    pass


@dataclasses.dataclass
class AudioManagerException(RequestException):
    file: Union[AudioSourceConfig, FileUrlData]
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None

    def describe_short(self) -> str:
        return str(self.exception.__class__.__name__ if self.exception else self.response.status_code)


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
