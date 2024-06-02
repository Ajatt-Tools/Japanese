# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import re
from collections.abc import Iterable
from collections.abc import MutableMapping, MutableSequence
from typing import NamedTuple, final

from aqt import mw

from .ajt_common.addon_config import AddonConfigManager, ConfigSubViewBase
from .helpers.audio_manager import AudioSourceConfig
from .helpers.profiles import Profile, get_default_profile
from .helpers.sakura_client import DictName, SearchType, AddDefBehavior
from .helpers.tokens import RE_FLAGS
from .mecab_controller.kana_conv import to_katakana
from .pitch_accents.styles import PitchPatternStyle


def split_words(config_value: str) -> list[str]:
    """Splits string by comma."""
    return re.split(r"[、, ]+", config_value, flags=RE_FLAGS)


class WordBlockListManager(ConfigSubViewBase):
    _NUMBERS = re.compile(r"[一二三四五六七八九十０１２３４５６７８９0123456789]+")

    @property
    def _should_skip_numbers(self) -> bool:
        return self["skip_numbers"] is True

    @property
    def blocklisted_words(self) -> list[str]:
        """Returns a user-defined list of blocklisted words."""
        return split_words(self["blocklisted_words"])

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""
        if to_katakana(word) in map(to_katakana, self.blocklisted_words):
            return True
        if self._should_skip_numbers and re.fullmatch(self._NUMBERS, word):
            return True
        return False


@enum.unique
class ReadingsDiscardMode(enum.Enum):
    keep_first = enum.auto()
    discard_extra = enum.auto()
    discard_all = enum.auto()


class PitchAndFuriganaCommon(WordBlockListManager):
    @property
    def maximum_results(self) -> int:
        return int(self["maximum_results"])

    @property
    def reading_separator(self) -> str:
        return self["reading_separator"]

    @property
    def discard_mode(self) -> ReadingsDiscardMode:
        return ReadingsDiscardMode[self["discard_mode"]]


@final
class FuriganaConfigView(PitchAndFuriganaCommon):
    _view_key: str = "furigana"

    @property
    def prefer_literal_pronunciation(self) -> bool:
        return self["prefer_literal_pronunciation"] is True

    @property
    def mecab_only(self) -> list[str]:
        """Words that shouldn't be looked up in the accent dictionary."""
        return split_words(self["mecab_only"])

    def can_lookup_in_db(self, word: str) -> bool:
        return self.maximum_results > 1 and word not in self.mecab_only


@final
class PitchConfigView(PitchAndFuriganaCommon):
    _view_key: str = "pitch_accent"

    @property
    def lookup_shortcut(self) -> str:
        return self["lookup_shortcut"]

    @property
    def output_hiragana(self) -> bool:
        return self["output_hiragana"] is True

    @property
    def kana_lookups(self) -> bool:
        return self["kana_lookups"] is True

    @property
    def word_separator(self) -> str:
        return self["word_separator"]

    @property
    def html_style(self) -> PitchPatternStyle:
        return PitchPatternStyle[self["html_style"]]


@final
class ContextMenuConfigView(ConfigSubViewBase):
    _view_key: str = "context_menu"

    @property
    def generate_furigana(self) -> bool:
        return self["generate_furigana"] is True

    @property
    def to_katakana(self) -> bool:
        return self["to_katakana"] is True

    @property
    def to_hiragana(self) -> bool:
        return self["to_hiragana"] is True

    @property
    def literal_pronunciation(self) -> bool:
        return self["literal_pronunciation"] is True


class ToolbarButtonConfig(NamedTuple):
    enabled: bool
    shortcut: str
    text: str


@final
class ToolbarConfigView(ConfigSubViewBase):
    _view_key: str = "toolbar"

    def __getitem__(self, item) -> ToolbarButtonConfig:
        try:
            return ToolbarButtonConfig(**super().__getitem__(item))
        except TypeError:
            return ToolbarButtonConfig(True, "", "？")

    @property
    def generate_all_button(self) -> ToolbarButtonConfig:
        return self["generate_all_button"]

    @property
    def regenerate_all_button(self) -> ToolbarButtonConfig:
        return self["regenerate_all_button"]

    @property
    def furigana_button(self) -> ToolbarButtonConfig:
        return self["furigana_button"]

    @property
    def hiragana_button(self) -> ToolbarButtonConfig:
        return self["hiragana_button"]

    @property
    def clean_furigana_button(self) -> ToolbarButtonConfig:
        return self["clean_furigana_button"]

    @property
    def audio_search_button(self) -> ToolbarButtonConfig:
        return self["audio_search_button"]

    @property
    def add_definition_button(self) -> ToolbarButtonConfig:
        return self["add_definition_button"]


@final
class AudioSettingsConfigView(ConfigSubViewBase):
    _view_key: str = "audio_settings"

    @property
    def dictionary_download_timeout(self) -> int:
        return self["dictionary_download_timeout"]

    @property
    def audio_download_timeout(self) -> int:
        return self["audio_download_timeout"]

    @property
    def attempts(self) -> int:
        return self["attempts"]

    @property
    def maximum_results(self) -> int:
        return self["maximum_results"]

    @property
    def ignore_inflections(self) -> bool:
        return bool(self["ignore_inflections"])

    @property
    def stop_if_one_source_has_results(self) -> bool:
        return bool(self["stop_if_one_source_has_results"])

    @property
    def search_dialog_dest_field_name(self) -> str:
        return self["search_dialog_dest_field_name"]

    @search_dialog_dest_field_name.setter
    def search_dialog_dest_field_name(self, field_name: str) -> None:
        self["search_dialog_dest_field_name"] = field_name

    @property
    def search_dialog_src_field_name(self) -> str:
        return self["search_dialog_src_field_name"]

    @search_dialog_src_field_name.setter
    def search_dialog_src_field_name(self, field_name: str) -> None:
        self["search_dialog_src_field_name"] = field_name

    @property
    def tag_separator(self) -> str:
        return self["tag_separator"]


@final
class DefinitionsConfigView(ConfigSubViewBase):
    _view_key: str = "definitions"

    @property
    def timeout(self) -> int:
        return self["timeout"]

    @property
    def remove_marks(self) -> bool:
        return bool(self["remove_marks"])

    @property
    def dict_name(self) -> DictName:
        return DictName[self["dict_name"]]

    @property
    def search_type(self) -> SearchType:
        return SearchType[self["search_type"]]

    @property
    def source(self) -> str:
        return self["source"]

    @property
    def destination(self) -> str:
        return self["destination"]

    @property
    def behavior(self) -> AddDefBehavior:
        return AddDefBehavior[self["behavior"]]


@final
class JapaneseConfig(AddonConfigManager):
    def __init__(self, default: bool = False) -> None:
        super().__init__(default)
        self._furigana = FuriganaConfigView(self)
        self._pitch = PitchConfigView(self)
        self._context_menu = ContextMenuConfigView(self)
        self._toolbar = ToolbarConfigView(self)
        self._audio_settings = AudioSettingsConfigView(self)
        self._definitions = DefinitionsConfigView(self)

    def iter_profiles(self) -> Iterable[Profile]:
        for profile_dict in self["profiles"]:
            # In case new options are added or removed in the future,
            # load default settings first, then overwrite them.
            default = get_default_profile(profile_dict["mode"])
            common_keys = dataclasses.asdict(default).keys() & profile_dict.keys()
            yield dataclasses.replace(
                default,
                **{key: profile_dict[key] for key in common_keys},
            )

    def iter_audio_sources(self) -> Iterable[AudioSourceConfig]:
        for source_dict in self.audio_sources:
            yield AudioSourceConfig(**source_dict)

    @property
    def audio_settings(self) -> AudioSettingsConfigView:
        return self._audio_settings

    @property
    def audio_sources(self) -> MutableSequence[MutableMapping]:
        return self["audio_sources"]

    @property
    def cache_lookups(self) -> int:
        return int(self["cache_lookups"])

    @property
    def furigana(self) -> FuriganaConfigView:
        return self._furigana

    @property
    def pitch_accent(self) -> PitchConfigView:
        return self._pitch

    @property
    def context_menu(self) -> ContextMenuConfigView:
        return self._context_menu

    @property
    def toolbar(self) -> ToolbarConfigView:
        return self._toolbar

    @property
    def definitions(self) -> DefinitionsConfigView:
        return self._definitions


if mw:
    config_view = JapaneseConfig()
