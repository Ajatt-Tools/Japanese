# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import abc
import re
from typing import List, Dict, Iterable, Tuple, NamedTuple

from .helpers.config import default_config, config


class WordBlockList:
    _NUMBERS = re.compile(r'[一二三四五六七八九十０１２３４５６７８９0123456789]+')

    def __init__(self, master_key: str):
        self._master_key = master_key

    @property
    def _dict(self):
        return config[self._master_key]

    @property
    def _should_skip_numbers(self):
        return self._dict.get('skip_numbers') is True

    @property
    def words(self) -> List[str]:
        """Returns a user-defined list of blocklisted words."""
        return re.split(r'[、, ]+', self._dict.get('blocklisted_words', str()), flags=re.IGNORECASE)

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""

        from .mecab_controller import to_katakana

        return (
                to_katakana(word) in map(to_katakana, self.words)
                or (self._should_skip_numbers and re.fullmatch(self._NUMBERS, word))
        )


class ConfigViewBase(abc.ABC):
    _master_key = None

    @property
    def _dict(self):
        return config[self._master_key] if self._master_key else config

    @property
    def _default_dict(self):
        return default_config[self._master_key] if self._master_key else default_config

    def iter_bools(self) -> Iterable[Tuple[str, bool]]:
        for key, default_value in self._default_dict.items():
            if type(default_value) == bool:
                yield key, self._dict.get(key, default_value)


class FuriganaConfigView(ConfigViewBase):
    _master_key = 'furigana'

    def __init__(self):
        super().__init__()
        self._blocklist = WordBlockList(self._master_key)

    @property
    def database_lookups(self) -> bool:
        return self._dict.get('database_lookups') is True

    @property
    def prefer_long_vowel_mark(self):
        return self._dict.get('prefer_long_vowel_mark') is True

    @property
    def reading_separator(self) -> str:
        return self._dict.get('reading_separator', ',')

    def can_lookup_in_db(self, word: str) -> bool:
        return self.database_lookups and word not in self._dict.get('mecab_only', '').split(',')

    def is_blocklisted(self, word: str) -> bool:
        return self._blocklist.is_blocklisted(word)

    @property
    def maximum_results(self) -> int:
        return int(self._dict.get('maximum_results', 3))

    @property
    def blocklisted_words(self) -> List[str]:
        return self._blocklist.words

    @property
    def mecab_only(self) -> List[str]:
        return re.split(r'[、, ]+', self._dict.get('mecab_only', str()), flags=re.IGNORECASE)


class PitchConfigView(ConfigViewBase):
    _master_key = 'pitch_accent'

    def __init__(self):
        super().__init__()
        self._blocklist = WordBlockList(self._master_key)

    @property
    def lookup_shortcut(self) -> str:
        return self._dict.get('lookup_shortcut')

    @property
    def use_mecab(self):
        return self._dict.get('use_mecab') is True

    @property
    def output_hiragana(self):
        return self._dict.get('output_hiragana') is True

    @property
    def kana_lookups(self):
        return self._dict.get('kana_lookups') is True

    @property
    def maximum_results(self) -> int:
        return int(self._dict.get('maximum_results', 3))

    @property
    def blocklisted_words(self) -> List[str]:
        return self._blocklist.words

    def is_blocklisted(self, word: str) -> bool:
        return self._blocklist.is_blocklisted(word)


class ContextMenuConfigView(ConfigViewBase):
    _master_key = 'context_menu'

    @property
    def generate_furigana(self):
        return self._dict.get('generate_furigana') is True

    @property
    def to_katakana(self):
        return self._dict.get('to_katakana') is True

    @property
    def to_hiragana(self):
        return self._dict.get('to_hiragana') is True


class ToolbarButtonConfig(NamedTuple):
    enabled: bool
    shortcut: str
    text: str


class ConfigView(ConfigViewBase):
    def __init__(self):
        super().__init__()
        self._furigana = FuriganaConfigView()
        self._pitch = PitchConfigView()
        self._context_menu = ContextMenuConfigView()

    @property
    def generate_on_note_add(self) -> bool:
        return self._dict.get('generate_on_note_add') is True

    @property
    def regenerate_readings(self) -> bool:
        return self._dict.get('regenerate_readings') is True

    @property
    def cache_lookups(self) -> int:
        return int(self._dict.get('cache_lookups', 1024))

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
    def toolbar(self) -> Dict[str, ToolbarButtonConfig]:
        return {
            key: ToolbarButtonConfig(**button_config)
            for key, button_config in self._dict['toolbar'].items()
        }


config_view = ConfigView()
