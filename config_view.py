# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from typing import List, Dict, Iterable, Tuple, NamedTuple, final, Any

from .helpers.config import default_config, config
from .helpers.mingle_readings import WordWrapMode
from .helpers.tokens import RE_FLAGS


def split_words(config_value: str) -> List[str]:
    """Splits string by comma."""
    return re.split(r'[、, ]+', config_value, flags=RE_FLAGS)


class ConfigViewBase:
    _view_key = None

    @property
    def _dict(self) -> Dict[str, Any]:
        return config[self._view_key] if self._view_key else config

    @property
    def _default_dict(self) -> Dict[str, Any]:
        return default_config[self._view_key] if self._view_key else default_config

    def get(self, key: str) -> Any:
        return self._dict.get(key, self._default_dict.get(key))

    def all(self) -> Iterable[Tuple[str, Any]]:
        for key, default_value in self._default_dict.items():
            yield key, self._dict.get(key, default_value)

    def bools(self) -> Iterable[Tuple[str, bool]]:
        for key, default_value in self._default_dict.items():
            if type(default_value) == bool:
                yield key, bool(self._dict.get(key, default_value))


class WordBlockListManager(ConfigViewBase):
    _NUMBERS = re.compile(r'[一二三四五六七八九十０１２３４５６７８９0123456789]+')

    @property
    def _should_skip_numbers(self) -> bool:
        return self.get('skip_numbers') is True

    @property
    def blocklisted_words(self) -> List[str]:
        """Returns a user-defined list of blocklisted words."""
        return split_words(self.get('blocklisted_words'))

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""

        from .mecab_controller import to_katakana

        return (
                to_katakana(word) in map(to_katakana, self.blocklisted_words)
                or (self._should_skip_numbers and re.fullmatch(self._NUMBERS, word))
        )


@final
class FuriganaConfigView(WordBlockListManager):
    _view_key = 'furigana'

    @property
    def prefer_long_vowel_mark(self) -> bool:
        return self.get('prefer_long_vowel_mark') is True

    @property
    def reading_separator(self) -> str:
        return self.get('reading_separator')

    @property
    def wrap_readings(self) -> WordWrapMode:
        return WordWrapMode[self.get('wrap_readings')]

    @property
    def maximum_results(self) -> int:
        return int(self.get('maximum_results'))

    @property
    def mecab_only(self) -> List[str]:
        return split_words(self.get('mecab_only'))

    @property
    def counters(self) -> List[str]:
        """Words that shouldn't be looked up in the accent dictionary."""
        return split_words(self.get('counters'))

    @property
    def database_lookups(self) -> bool:
        return self.get('database_lookups') is True

    def can_lookup_in_db(self, word: str) -> bool:
        return self.database_lookups and word not in self.mecab_only


@final
class PitchConfigView(WordBlockListManager):
    _view_key = 'pitch_accent'

    @property
    def lookup_shortcut(self) -> str:
        return self.get('lookup_shortcut')

    @property
    def use_mecab(self) -> bool:
        return self.get('use_mecab') is True

    @property
    def output_hiragana(self) -> bool:
        return self.get('output_hiragana') is True

    @property
    def kana_lookups(self) -> bool:
        return self.get('kana_lookups') is True

    @property
    def maximum_results(self) -> int:
        return int(self.get('maximum_results'))

    @property
    def reading_separator(self) -> str:
        return self.get('reading_separator')

    @property
    def word_separator(self) -> str:
        return self.get('word_separator')


@final
class ContextMenuConfigView(ConfigViewBase):
    _view_key = 'context_menu'

    @property
    def generate_furigana(self) -> bool:
        return self.get('generate_furigana') is True

    @property
    def to_katakana(self) -> bool:
        return self.get('to_katakana') is True

    @property
    def to_hiragana(self) -> bool:
        return self.get('to_hiragana') is True


class ToolbarButtonConfig(NamedTuple):
    enabled: bool
    shortcut: str
    text: str


@final
class ToolbarConfigView(ConfigViewBase):
    _view_key = 'toolbar'

    def get(self, key: str) -> ToolbarButtonConfig:
        return ToolbarButtonConfig(**super().get(key))

    def all(self) -> Iterable[Tuple[str, ToolbarButtonConfig]]:
        """ Get all button configs. """
        for key, button_config in super().all():
            yield key, ToolbarButtonConfig(**button_config)

    @property
    def regenerate_all_button(self) -> ToolbarButtonConfig:
        return self.get('regenerate_all_button')

    @property
    def furigana_button(self) -> ToolbarButtonConfig:
        return self.get('furigana_button')

    @property
    def clean_furigana_button(self) -> ToolbarButtonConfig:
        return self.get('clean_furigana_button')


@final
class ConfigView(ConfigViewBase):
    def __init__(self):
        super().__init__()
        self._furigana = FuriganaConfigView()
        self._pitch = PitchConfigView()
        self._context_menu = ContextMenuConfigView()
        self._toolbar = ToolbarConfigView()

    @property
    def generate_on_note_add(self) -> bool:
        return self.get('generate_on_note_add') is True

    @property
    def regenerate_readings(self) -> bool:
        return self.get('regenerate_readings') is True

    @property
    def cache_lookups(self) -> int:
        return int(self.get('cache_lookups'))

    @property
    def styles(self) -> Dict[str, str]:
        return self._dict['styles']

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
