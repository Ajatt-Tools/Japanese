# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
from typing import Optional, Union

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

    def as_config_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass
class AudioManagerException(RequestException):
    file: Union[AudioSourceConfig, FileUrlData]
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None

    def describe_short(self) -> str:
        return str(self.exception.__class__.__name__ if self.exception else self.response.status_code)
