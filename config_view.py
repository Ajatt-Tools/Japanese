# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import enum
import re
from typing import List, Dict, Iterable, NamedTuple, final

from .ajt_common.addon_config import AddonConfigManager
from .helpers.profiles import Profile
from .helpers.tokens import RE_FLAGS


def split_words(config_value: str) -> list[str]:
    """Splits string by comma."""
    return re.split(r'[、, ]+', config_value, flags=RE_FLAGS)


class ConfigViewBase(AddonConfigManager):
    _view_key = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._view_key is not None:
            self._config = self._config[self._view_key]
            self._default_config = self._default_config[self._view_key]

    def write_config(self):
        if self._view_key is not None:
            raise RuntimeError("Can't call this function from a sub-view.")
        return super().write_config()


class WordBlockListManager(ConfigViewBase):
    _NUMBERS = re.compile(r'[一二三四五六七八九十０１２３４５６７８９0123456789]+')

    @property
    def _should_skip_numbers(self) -> bool:
        return self['skip_numbers'] is True

    @property
    def blocklisted_words(self) -> list[str]:
        """Returns a user-defined list of blocklisted words."""
        return split_words(self['blocklisted_words'])

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""

        from .mecab_controller import to_katakana

        return (
                to_katakana(word) in map(to_katakana, self.blocklisted_words)
                or (self._should_skip_numbers and re.fullmatch(self._NUMBERS, word))
        )


@enum.unique
class ReadingsDiscardMode(enum.Enum):
    keep_first = enum.auto()
    discard_extra = enum.auto()
    discard_all = enum.auto()


class PitchAndFuriganaCommon(WordBlockListManager):
    @property
    def maximum_results(self) -> int:
        return int(self['maximum_results'])

    @property
    def reading_separator(self) -> str:
        return self['reading_separator']

    @property
    def discard_mode(self) -> ReadingsDiscardMode:
        return ReadingsDiscardMode[self['discard_mode']]


@final
class FuriganaConfigView(PitchAndFuriganaCommon):
    _view_key = 'furigana'

    @property
    def prefer_literal_pronunciation(self) -> bool:
        return self['prefer_literal_pronunciation'] is True

    @property
    def mecab_only(self) -> list[str]:
        """Words that shouldn't be looked up in the accent dictionary."""
        return split_words(self['mecab_only'])

    @property
    def counters(self) -> list[str]:
        """Words that shouldn't be looked up in the accent dictionary."""
        return split_words(self['counters'])

    @property
    def database_lookups(self) -> bool:
        return self['database_lookups'] is True

    def can_lookup_in_db(self, word: str) -> bool:
        return self.database_lookups and word not in self.mecab_only


@final
class PitchConfigView(PitchAndFuriganaCommon):
    _view_key = 'pitch_accent'

    @property
    def lookup_shortcut(self) -> str:
        return self['lookup_shortcut']

    @property
    def output_hiragana(self) -> bool:
        return self['output_hiragana'] is True

    @property
    def kana_lookups(self) -> bool:
        return self['kana_lookups'] is True

    @property
    def word_separator(self) -> str:
        return self['word_separator']


@final
class ContextMenuConfigView(ConfigViewBase):
    _view_key = 'context_menu'

    @property
    def generate_furigana(self) -> bool:
        return self['generate_furigana'] is True

    @property
    def to_katakana(self) -> bool:
        return self['to_katakana'] is True

    @property
    def to_hiragana(self) -> bool:
        return self['to_hiragana'] is True

    @property
    def literal_pronunciation(self) -> bool:
        return self['literal_pronunciation'] is True


class ToolbarButtonConfig(NamedTuple):
    enabled: bool
    shortcut: str
    text: str


@final
class ToolbarConfigView(ConfigViewBase):
    _view_key = 'toolbar'

    def __getitem__(self, item) -> ToolbarButtonConfig:
        try:
            return ToolbarButtonConfig(**super().__getitem__(item))
        except TypeError:
            return ToolbarButtonConfig(True, "", "？")

    @property
    def regenerate_all_button(self) -> ToolbarButtonConfig:
        return self['regenerate_all_button']

    @property
    def furigana_button(self) -> ToolbarButtonConfig:
        return self['furigana_button']

    @property
    def hiragana_button(self) -> ToolbarButtonConfig:
        return self['hiragana_button']

    @property
    def clean_furigana_button(self) -> ToolbarButtonConfig:
        return self['clean_furigana_button']


@final
class ConfigView(ConfigViewBase):
    def __init__(self):
        super().__init__()
        self._furigana = FuriganaConfigView()
        self._pitch = PitchConfigView()
        self._context_menu = ContextMenuConfigView()
        self._toolbar = ToolbarConfigView()

    def iter_profiles(self) -> Iterable[Profile]:
        for profile_dict in self['profiles']:
            # In case new options are added in the future,
            # load default settings first, then overwrite them.
            default = Profile.class_by_mode(profile_dict['mode']).new()
            yield Profile(**(dataclasses.asdict(default) | profile_dict))

    @property
    def generate_on_note_add(self) -> bool:
        return self['generate_on_note_add'] is True

    @property
    def regenerate_readings(self) -> bool:
        return self['regenerate_readings'] is True

    @property
    def cache_lookups(self) -> int:
        return int(self['cache_lookups'])

    @property
    def styles(self) -> dict[str, str]:
        return self['styles']

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


config_view = ConfigView()
