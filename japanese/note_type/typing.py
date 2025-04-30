# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import typing


class AnkiCardTemplateDict(typing.TypedDict):
    qfmt: str
    afmt: str
    name: str  # card template name, e.g. "recognition", "production".


class AnkiNoteTypeDict(typing.TypedDict):
    tmpls: list[AnkiCardTemplateDict]
    css: str
    name: str  # model name
