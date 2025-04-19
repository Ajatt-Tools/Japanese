# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import base64
import dataclasses
import enum
import re
import sys
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup, PageElement, ResultSet, Tag

from ..config_view import ForvoAudioFormat, ForvoSettingsConfigView
from ..helpers.http_client import create_session
from .basic_types import AudioManagerExceptionBase, FileUrlData
from .source_manager import normalize_filename


# Config default values
@dataclasses.dataclass
class ForvoConfig:
    enable_forvo_search: bool = True
    language: str = "ja"
    preferred_usernames: list[str] = dataclasses.field(default_factory=list)
    preferred_countries: list[str] = dataclasses.field(default_factory=list)
    show_gender: bool = True
    show_country: bool = True
    timeout_seconds: int = 5
    retry_attempts: int = 3
    audio_format: ForvoAudioFormat = ForvoAudioFormat.ogg

    def __post_init__(self) -> None:
        self.language = self.language.lower()
        self.preferred_usernames = [user.lower() for user in self.preferred_usernames]
        self.preferred_countries = [country.lower() for country in self.preferred_countries]


def decode_play_arg(play_arg: str) -> str:
    """
    Convert play arg to relative path to file.
    E.g. 'OTQ3ODA1OS83Ni85NDc4MDU5Xzc2XzEzMjg3Lm1wMw==' -> '9478059/76/9478059_76_13287.mp3'
    """
    return base64.b64decode(play_arg).decode("utf-8")


def file_type(file: str) -> str:
    """
    Return file type (file extension).
    E.g. '9478059/76/9478059_76_13287.mp3' -> 'mp3'
    """
    return file.split(".")[-1]


class ForvoGender(enum.Enum):
    male = "♂"
    female = "♀"


@dataclasses.dataclass
class ForvoPronunciation:
    word: str
    username: str
    audio_url: str
    gender: Optional[ForvoGender] = None
    country: Optional[str] = None


@dataclasses.dataclass
class ForvoFilenameBuilder:
    show_gender: bool
    show_country: bool

    def make_filename(self, audio: ForvoPronunciation) -> str:
        components = [
            audio.word,
            "forvo",
            audio.username,
        ]
        if self.show_gender and audio.gender:
            components.append(audio.gender.value)
        if self.show_country and audio.country:
            components.append(audio.country)
        return "_".join(components) + f".{file_type(audio.audio_url)}"


RE_FIND_USERNAME = re.compile(r"Pronunciation by(?P<username>[^()]+)")
RE_FIND_GENDER = re.compile(r"\((?P<gender>Male|Female)")
RE_FIND_COUNTRY = re.compile(r"\((?:Male|Female) from (?P<country>[^()]+)")
RE_SPACES = re.compile(r"\s+")


def find_username(result: PageElement) -> str:
    """
    Capture the username of the user.
    """
    # Some users have deleted accounts which is why can't just parse it from the <a> tag
    # Find text like this: 'Pronunciation bystrawberrybrown(Female from Japan)'
    if match := re.search(RE_FIND_USERNAME, result.get_text(strip=True)):
        return match.group("username").strip()
    return "Unknown"


def find_gender(result: PageElement) -> Optional[ForvoGender]:
    if match := re.search(RE_FIND_GENDER, result.get_text(strip=True)):
        # noinspection PyTypeChecker
        return ForvoGender[match.group("gender").strip().lower()]
    return None


def find_country(result: PageElement) -> Optional[str]:
    if match := re.search(RE_FIND_COUNTRY, result.get_text(strip=True)):
        return match.group("country").strip()
    return None


def audio_transcription_from_play_button(element: Tag) -> str:
    return re.sub(RE_SPACES, "_", element.text.removesuffix("pronunciation").strip())


def make_search_result_filename(audio_url: str, word: str, lang: str) -> str:
    """
    For search result the author (username) is unknown. Omit their name, country, gender, etc.
    """
    suffix = f"_forvo_{lang}.{file_type(audio_url)}"
    return normalize_filename(word, suffix_size=len(suffix)) + suffix


@dataclasses.dataclass(frozen=True)
class ForvoClientException(AudioManagerExceptionBase):
    word: str
    explanation: str
    response: Optional[requests.Response] = None
    exception: Optional[Exception] = None

    def __str__(self) -> str:
        return self.explanation


@dataclasses.dataclass
class FullForvoResult:
    """
    Used to retrieve all results when using Anki's QueryOp
    """

    error_word: Optional[Exception] = None
    error_search: Optional[Exception] = None
    files: list[FileUrlData] = dataclasses.field(default_factory=list)


class ForvoClient:
    """
    Forvo web-scraper utility.
    """

    _server_host: str = "https://forvo.com"
    _audio_http_host: str = "https://audio12.forvo.com"
    _config: Union[ForvoConfig, ForvoSettingsConfigView]
    _session: requests.Session

    def __init__(self, config: Union[ForvoConfig, ForvoSettingsConfigView]) -> None:
        self._config = config
        self._session = create_session(self._config.retry_attempts)

    def _restart_session(self) -> None:
        self._session.close()
        self._session = create_session(self._config.retry_attempts)

    def _word_url(self, word: str) -> str:
        return f"{self._server_host}/word/{word}/"

    def _search_url(self, word: str) -> str:
        return f"{self._server_host}/search/{word}/{self._config.language}/"

    def _http_get(self, word: str, *, is_search: bool = False) -> requests.Response:
        try:
            response = self._session.get(
                url=(self._search_url(word) if is_search else self._word_url(word)),
                timeout=self._config.timeout_seconds,
            )
        except OSError as ex:
            self._restart_session()
            raise ForvoClientException(
                word=word,
                explanation=f"Forvo access failed with exception {ex.__class__.__name__}",
                exception=ex,
            )
        if response.status_code != requests.codes.ok:
            self._restart_session()
            raise ForvoClientException(
                word=word,
                explanation=f"Forvo access failed with return code {response.status_code} ({response.reason})",
                response=response,
            )
        return response

    def find_pronunciations(self, results: ResultSet, word: str) -> list[ForvoPronunciation]:
        pronunciations: list[ForvoPronunciation] = []
        for result in results:
            pronunciation = ForvoPronunciation(
                word=word,
                username=find_username(result),
                audio_url=self._extract_url(result.div),
            )
            if self._config.show_gender:
                pronunciation.gender = find_gender(result)
            if self._config.show_country or self._config.preferred_countries:
                pronunciation.country = find_country(result)
            pronunciations.append(pronunciation)
        return pronunciations

    def sort_pronunciations(self, pronunciations: list[ForvoPronunciation]) -> list[ForvoPronunciation]:
        """
        Order the list based on preferred_usernames and preferred_countries
        Preferred usernames takes priority over preferred countries
        """

        def username_key(pronunciation: ForvoPronunciation) -> int:
            try:
                return self._config.preferred_usernames.index(pronunciation.username.lower())
            except ValueError:
                return sys.maxsize

        def country_key(pronunciation: ForvoPronunciation) -> int:
            try:
                return self._config.preferred_countries.index(pronunciation.country.lower())
            except ValueError:
                return sys.maxsize

        def sort_key(pronunciation: ForvoPronunciation) -> tuple[int, int]:
            # If the username isn't in the preferred lists, put it at the end
            return username_key(pronunciation), country_key(pronunciation)

        return sorted(pronunciations, key=sort_key)

    def _extract_url(self, element: Tag) -> str:
        play = element["onclick"]
        # We are interested in Forvo's javascript Play function which takes in some parameters to play the audio
        # Example: Play(3060224,'OTQyN...','OTQyN..',false,'Yy9wL2NwXzk0MjYzOTZfNzZfMzM1NDkxNS5tcDM=','Yy9wL...','h')
        # Match anything that isn't commas, parentheses or quotes to capture the function arguments
        # Regex will match something like ["Play", "3060224", ...]
        play_args = re.findall(r"([^',()]+)", play)[1:]

        # Forvo has two locations for mp3, /audios/mp3 and just /mp3
        # /audios/mp3 is normalized and has the filename in the 5th argument of Play base64 encoded
        # /mp3 is raw and has the filename in the 2nd argument of Play encoded

        if self._config.audio_format == ForvoAudioFormat.ogg:
            normalized_arg, raw_arg = 5, 2
        elif self._config.audio_format == ForvoAudioFormat.mp3:
            normalized_arg, raw_arg = 4, 1
        else:
            raise ValueError(f"unsupported audio format: {self._config.audio_format.name}")

        try:
            file = decode_play_arg(play_args[normalized_arg])
            return f"{self._audio_http_host}/audios/{file_type(file)}/{file}"
        except (ValueError, IndexError):
            # Some pronunciations don't have a normalized version so fallback to raw
            file = decode_play_arg(play_args[raw_arg])
            return f"{self._audio_http_host}/{file_type(file)}/{file}"

    def word(self, word: str) -> list[FileUrlData]:
        """
        Scrape forvo's word page for audio sources.
        """
        word = word.strip()
        if not word:
            return []
        resp = self._http_get(word, is_search=False)
        soup = BeautifulSoup(resp.text, features="html.parser")

        # Forvo's word page returns multiple result sets grouped by langauge like:
        # <div id="language-container-ja">
        #   <article>
        #       <ul class="show-all-pronunciations">
        #           <li>
        #              <span class="play" onclick"(some javascript to play the word audio)"></span>
        #                "Pronunciation by <span><a href="/username/link">skent</a></span>"
        #              <div class="more">...</div>
        #           </li>
        #       </ul>
        #       ...
        #   </article>
        #   <article id="extra-word-info-76">...</article>
        # </ul>
        # We also filter out ads
        results = soup.select(
            f"#language-container-{self._config.language}>article>ul.pronunciations-list>li:not(.li-ad)"
        )
        pronunciations = self.find_pronunciations(results, word)

        # Order the list based on preferred_usernames and preferred_countries
        # preferred usernames takes priority over preferred countries
        if self._config.preferred_usernames or self._config.preferred_countries:
            pronunciations = self.sort_pronunciations(pronunciations)

        # Transform the list of pronunciations into AJT Japanese format
        return [
            FileUrlData(
                url=pronunciation.audio_url,
                desired_filename=ForvoFilenameBuilder(
                    show_country=self._config.show_country,
                    show_gender=self._config.show_gender,
                ).make_filename(pronunciation),
                word=word,
                source_name="Forvo Word",
            )
            for pronunciation in pronunciations
        ]

    def search(self, word: str) -> list[FileUrlData]:
        """
        Scrape Forvo's search page for audio sources. Note that the search page omits the username
        """
        word = word.strip()
        if not word:
            return []
        resp = self._http_get(word, is_search=True)
        soup = BeautifulSoup(resp.text, features="html.parser")

        # Forvo's search page returns two result sets like:
        # <ul class="word-play-list-icon-size-l">
        #   <li><span class="play" onclick"(some javascript to play the word audio)"></li>
        # </ul>
        results = soup.select("ul.word-play-list-icon-size-l>li>div.play")

        # Transform the list of pronunciations into AJT Japanese format
        return [
            FileUrlData(
                url=(url := self._extract_url(result)),
                desired_filename=make_search_result_filename(
                    url,
                    audio_transcription_from_play_button(result),
                    self._config.language,
                ),
                word=word,
                source_name="Forvo Search",
            )
            for result in results
        ]

    def full_search(self, query: str) -> FullForvoResult:
        """
        Perform word search and normal search.
        """
        full_result = FullForvoResult()
        audio_files: dict[str, FileUrlData] = {}
        try:
            for result in self.word(query):
                audio_files[result.url] = result
        except Exception as ex:
            full_result.error_word = ex
        try:
            for result in self.search(query):
                if result.url not in audio_files:
                    audio_files[result.url] = result
        except Exception as ex:
            full_result.error_search = ex
        full_result.files = [*audio_files.values()]
        return full_result
