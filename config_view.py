import abc
import itertools
import re
from typing import List, Dict, Any, Iterable, Tuple


class WordBlockList:
    _NUMBERS = "一二三四五六七八九十０１２３４５６７８９"

    def __init__(self, config: Dict[str, Any]):
        self._dict = config

    @property
    def _should_skip_numbers(self):
        return self._dict.get('skip_numbers') is True

    @property
    def words(self) -> List[str]:
        """Returns a user-defined list of blocklisted words."""
        return re.split(r'[、, ]+', self._dict.get('blocklisted_words', str()), flags=re.IGNORECASE)

    @property
    def numbers(self) -> Iterable[str]:
        """ Iterates blocklisted numbers, if enabled. """
        if self._should_skip_numbers:
            for c in self._NUMBERS:
                yield c

    def is_blocklisted(self, word: str) -> bool:
        """Returns True if the user specified that the word should not be looked up."""

        from .mecab_controller import to_katakana

        return to_katakana(word) in map(to_katakana, itertools.chain(self.words, self.numbers))


class ConfigViewBase(abc.ABC):
    _dict = None

    def iter_bools(self) -> Iterable[Tuple[str, bool]]:
        for key, value in self._dict.items():
            if type(value) == bool:
                yield key, value


class FuriganaConfigView(ConfigViewBase):
    def __init__(self):
        from .helpers.config import config

        self._dict = config['furigana']
        self._blocklist = WordBlockList(self._dict)

    @property
    def database_lookups(self) -> bool:
        return self._dict.get('database_lookups') is True

    @property
    def reading_separator(self) -> str:
        return self._dict.get('reading_separator', ',')

    def can_lookup_db(self, word: str) -> bool:
        return self.database_lookups and word not in self._dict.get('mecab_only', '').split(',')

    def is_blocklisted(self, word: str) -> bool:
        return self._blocklist.is_blocklisted(word)

    @property
    def blocklisted_words(self) -> List[str]:
        return self._blocklist.words


class PitchConfigView(ConfigViewBase):
    def __init__(self):
        from .helpers.config import config

        self._dict = config['pitch_accent']
        self._blocklist = WordBlockList(self._dict)

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
    def blocklisted_words(self) -> List[str]:
        return self._blocklist.words

    def is_blocklisted(self, word: str) -> bool:
        return self._blocklist.is_blocklisted(word)


class ConfigView(ConfigViewBase):
    def __init__(self):
        from .helpers.config import config
        self._dict = config
        self._furigana = FuriganaConfigView()
        self._pitch = PitchConfigView()

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
    def furigana(self) -> FuriganaConfigView:
        return self._furigana

    @property
    def pitch_accent(self) -> PitchConfigView:
        return self._pitch


config_view = ConfigView()
