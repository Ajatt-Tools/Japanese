import re
from types import SimpleNamespace
from typing import List, Dict, Any


class WordBlockList:
    _NUMBERS = "一二三四五六七八九十０１２３４５６７８９"

    def __init__(self, config: Dict[str, Any]):
        self._dict = config

    @property
    def _should_skip_numbers(self):
        return self._dict.get('skip_numbers') is True

    @property
    def _blocklisted_words(self) -> List[str]:
        """Returns a user-defined list of blocklisted words."""
        words = re.split(r'[、, ]+', self._dict.get('blocklisted_words', str()), flags=re.IGNORECASE)
        if self._should_skip_numbers:
            words.extend(self._NUMBERS)
        return words

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""

        from .mecab_controller import to_katakana

        return to_katakana(word) in map(to_katakana, self._blocklisted_words)


class ConfigView:
    def __init__(self):
        from .helpers.config import config
        self._dict = config

    @property
    def generate_on_note_add(self) -> bool:
        return self._dict['generate_on_note_add'] is True

    @property
    def regenerate_readings(self) -> bool:
        return self._dict['regenerate_readings'] is True

    @property
    def cache_lookups(self) -> int:
        return int(self._dict['cache_lookups'])

    @property
    def styles(self) -> Dict[str, str]:
        return self._dict['styles']

    @property
    def furigana(self):
        furigana_config = self._dict['furigana']
        return SimpleNamespace(
            database_lookups=furigana_config.get('database_lookups') is True,
            is_blocklisted=WordBlockList(furigana_config).is_blocklisted,
        )

    @property
    def pitch_accent(self):
        pitch_config = self._dict['pitch_accent']
        return SimpleNamespace(
            lookup_shortcut=pitch_config.get('lookup_shortcut'),
            use_mecab=pitch_config.get('use_mecab') is True,
            use_hiragana=pitch_config.get('use_hiragana') is True,
            kana_lookups=pitch_config.get('kana_lookups') is True,
            is_blocklisted=WordBlockList(pitch_config).is_blocklisted,
        )


config_view = ConfigView()
