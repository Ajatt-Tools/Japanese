# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import functools
import re
from collections.abc import Iterable, MutableSequence, Sequence
from typing import NamedTuple, final

from aqt import mw

from .ajt_common.addon_config import AddonConfigManager, ConfigSubViewBase
from .audio_manager.abstract import AudioSettingsConfigViewABC
from .audio_manager.basic_types import AudioSourceConfig, AudioSourceConfigDict
from .helpers.profiles import Profile
from .helpers.sakura_client import AddDefBehavior, DictName, SearchType
from .helpers.tokens import RE_FLAGS
from .mecab_controller.kana_conv import to_katakana
from .pitch_accents.styles import HTMLPitchPatternStyle

RE_CFG_WORD_SEP = re.compile(r"[\n;、, ]+", flags=RE_FLAGS)


@functools.lru_cache(maxsize=50)
def split_cfg_words(config_value: str) -> Sequence[str]:
    """Splits string by comma. Cache identical values."""
    return tuple(dict.fromkeys(re.split(RE_CFG_WORD_SEP, config_value)))


@functools.lru_cache(maxsize=50)
def as_lower_str_list(values: Sequence[str]) -> Sequence[str]:
    return [value.lower() for value in values]


class WordBlockListManager(ConfigSubViewBase):
    _NUMBERS = re.compile(r"[一二三四五六七八九十０１２３４５６７８９0123456789]+")

    @property
    def _should_skip_numbers(self) -> bool:
        return self["skip_numbers"] is True

    @property
    def blocklisted_words(self) -> Sequence[str]:
        """Returns a user-defined list of blocklisted words."""
        return split_cfg_words(self["blocklisted_words"])

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""
        if to_katakana(word) in map(to_katakana, self.blocklisted_words):
            return True
        if self._should_skip_numbers and re.fullmatch(self._NUMBERS, word):
            return True
        return False


class PitchAndFuriganaCommon(WordBlockListManager):
    @property
    def maximum_results(self) -> int:
        return int(self["maximum_results"])

    @property
    def reading_separator(self) -> str:
        return self["reading_separator"]


@final
class FuriganaConfigView(PitchAndFuriganaCommon):
    _view_key: str = "furigana"

    @property
    def prefer_literal_pronunciation(self) -> bool:
        return self["prefer_literal_pronunciation"] is True

    @property
    def mecab_only(self) -> Sequence[str]:
        """Words that shouldn't be looked up in the accent dictionary."""
        return split_cfg_words(self["mecab_only"])

    def can_lookup_in_db(self, word: str) -> bool:
        return self.maximum_results > 1 and (word not in self.mecab_only)

    @property
    def maximum_pitch_accents(self) -> int:
        return int(self["maximum_pitch_accents"])


@enum.unique
class LookupDialogPitchOutputFormat(enum.Enum):
    svg = enum.auto()
    html = enum.auto()


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
    def html_style(self) -> HTMLPitchPatternStyle:
        return HTMLPitchPatternStyle[self["html_style"]]

    @property
    def lookup_pitch_format(self) -> LookupDialogPitchOutputFormat:
        try:
            return LookupDialogPitchOutputFormat[self["lookup_pitch_format"]]
        except KeyError:
            return LookupDialogPitchOutputFormat.svg


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


@final
class AudioSettingsConfigView(ConfigSubViewBase, AudioSettingsConfigViewABC):
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


@enum.unique
class ForvoAudioFormat(enum.Enum):
    mp3 = enum.auto()
    ogg = enum.auto()


@final
class ForvoSettingsConfigView(ConfigSubViewBase):
    _view_key: str = "forvo"

    @property
    def enable_forvo_search(self) -> bool:
        return bool(self["enable_forvo_search"])

    @property
    def language(self) -> str:
        """Audio language. Other languages will be skipped."""
        return self["language"].lower()

    @property
    def preferred_usernames(self) -> Sequence[str]:
        """Returns a user-defined list of preferred usernames."""
        return as_lower_str_list(split_cfg_words(self["preferred_usernames"]))

    @property
    def preferred_countries(self) -> Sequence[str]:
        """Returns a user-defined list of preferred countries."""
        return as_lower_str_list(split_cfg_words(self["preferred_countries"]))

    @property
    def show_gender(self) -> bool:
        return bool(self["show_gender"])

    @property
    def show_country(self) -> bool:
        return bool(self["show_country"])

    @property
    def timeout_seconds(self) -> int:
        return int(self["timeout_seconds"])

    @property
    def retry_attempts(self) -> int:
        return int(self["retry_attempts"])

    @property
    def audio_format(self) -> ForvoAudioFormat:
        try:
            return ForvoAudioFormat[self["audio_format"]]
        except KeyError:
            return ForvoAudioFormat.ogg


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
class SvgPitchGraphOptionsConfigView(ConfigSubViewBase):
    _view_key: str = "svg_graphs"

    @property
    def include_text(self) -> bool:
        return self["include_text"] is True

    @property
    def graph_horizontal_padding(self) -> int:
        return self["graph_horizontal_padding"]

    @property
    def size_unit(self) -> int:
        return self["size_unit"]

    @property
    def x_step(self) -> int:
        return self["x_step"]

    @property
    def text_dx(self) -> int:
        return self["text_dx"]

    @property
    def tspan_dx(self) -> int:
        return self["tspan_dx"]

    @property
    def graph_height(self) -> int:
        return self["graph_height"]

    @property
    def graph_visible_height(self) -> int:
        return self["graph_visible_height"]

    @property
    def stroke_width(self) -> float:
        return self["stroke_width"]

    @property
    def circle_radius(self) -> float:
        return self["circle_radius"]

    @property
    def font_size(self) -> float:
        return self["font_size"]

    @property
    def letter_spacing(self) -> float:
        return self["letter_spacing"]

    @property
    def devoiced_circle_width(self) -> float:
        return self["devoiced_circle_width"]

    @property
    def devoiced_circle_radius(self) -> float:
        return self["devoiced_circle_radius"]

    @property
    def devoiced_circle_dy(self) -> int:
        return self["devoiced_circle_dy"]

    @property
    def devoiced_rectangle_padding(self) -> float:
        return self["devoiced_rectangle_padding"]

    @property
    def devoiced_stroke_dasharray(self) -> str:
        return self["devoiced_stroke_dasharray"]

    graph_font: str = "Noto Sans, Noto Sans CJK JP, IPAexGothic, IPAPGothic, IPAGothic, Yu Gothic, Sans, Sans-Serif"


class JapaneseConfig(AddonConfigManager):
    def __init__(self, default: bool = False) -> None:
        super().__init__(default)
        self._furigana = FuriganaConfigView(self)
        self._pitch = PitchConfigView(self)
        self._context_menu = ContextMenuConfigView(self)
        self._toolbar = ToolbarConfigView(self)
        self._audio_settings = AudioSettingsConfigView(self)
        self._forvo_settings = ForvoSettingsConfigView(self)
        self._svg_graphs = SvgPitchGraphOptionsConfigView(self)

    def iter_profiles(self) -> Iterable[Profile]:
        for profile_dict in self["profiles"]:
            yield Profile.from_config_dict(profile_dict)

    def iter_audio_sources(self) -> Iterable[AudioSourceConfig]:
        for source_dict in self.audio_sources:
            yield AudioSourceConfig(**source_dict)

    @property
    def audio_settings(self) -> AudioSettingsConfigView:
        return self._audio_settings

    @property
    def forvo(self) -> ForvoSettingsConfigView:
        return self._forvo_settings

    @property
    def audio_sources(self) -> MutableSequence[AudioSourceConfigDict]:
        return self["audio_sources"]

    @property
    def cache_lookups(self) -> int:
        return int(self["cache_lookups"])

    @property
    def insert_scripts_into_templates(self) -> bool:
        return bool(self["insert_scripts_into_templates"])

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
    def svg_graphs(self) -> SvgPitchGraphOptionsConfigView:
        return self._svg_graphs

    @property
    def show_welcome_guide(self) -> bool:
        return self["show_welcome_guide"] is True

    @show_welcome_guide.setter
    def show_welcome_guide(self, value: bool) -> None:
        self["show_welcome_guide"] = value

    def del_deprecated_keys(self) -> None:
        assert self.is_default is False
        for key in tuple(self.config.keys()):
            if key not in self.default_config:
                del self.config[key]
                print(f"removed deprecated config key: {key}")


if mw:
    config_view = JapaneseConfig()
