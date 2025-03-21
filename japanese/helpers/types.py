# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import typing


class SourceConfigDict(typing.TypedDict):
    enabled: bool
    name: str
    url: str


@dataclasses.dataclass
class SourceConfig:
    """
    Audio source or dictionary source.
    """

    enabled: bool
    name: str
    url: str

    @property
    def is_valid(self) -> bool:
        return bool(self.name and self.url)

    def as_config_dict(self) -> SourceConfigDict:
        return dataclasses.asdict(self)
