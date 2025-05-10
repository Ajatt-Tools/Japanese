# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum
import re
import typing
from types import SimpleNamespace

import anki.httpclient
import bs4
import requests
from bs4 import BeautifulSoup

DEF_SEP = "<br>"
SITE_URL = "https://sakura-paris.org"


@enum.unique
class SearchType(enum.Enum):
    prefix = "前方一致"
    suffix = "後方一致"
    exact = "完全一致"


@enum.unique
class DictName(enum.Enum):
    meikyou = "明鏡国語辞典"
    daijirin = "大辞林"
    daijisen = "大辞泉"
    shinmeikai = "新明解国語辞典"
    koujien = "広辞苑"
    shinjirin = "ハイブリッド新辞林"


@enum.unique
class AddDefBehavior(enum.Enum):
    append = enum.auto(), lambda field_value, fetched_value: f"{field_value}{DEF_SEP}{fetched_value}"
    prepend = enum.auto(), lambda field_value, fetched_value: f"{fetched_value}{DEF_SEP}{field_value}"
    replace = enum.auto(), lambda field_value, fetched_value: fetched_value

    def format(self, field_value: str, fetched_value: str):
        return self.value[-1](field_value, fetched_value).removeprefix(DEF_SEP).removesuffix(DEF_SEP)


def format_get_url(headword: str, dict_name: DictName, search_type: SearchType):
    return f"{SITE_URL}/dict/{dict_name.value}/{search_type.name}/{headword}"


class SakuraParisConfig(typing.Protocol):
    timeout: int
    remove_marks: bool
    dict_name: DictName
    search_type: SearchType
    source: str
    destination: str
    behavior: AddDefBehavior


class SakuraParisClient(anki.httpclient.HttpClient):
    timeout = 10
    _re_self_link = re.compile(r"^/dict/")

    def __init__(self, config: SakuraParisConfig, progress_hook=None) -> None:
        super().__init__(progress_hook)
        self._config = config

    def fetch_def(self, headword: str, *, dict_name: DictName = None, search_type: SearchType = None) -> str:
        self.timeout = self._config.timeout
        url = format_get_url(
            headword,
            dict_name=(dict_name or self._config.dict_name),
            search_type=(search_type or self._config.search_type),
        )
        with self.get(url) as r:
            if r.status_code != requests.codes.ok:
                return ""
            return DEF_SEP.join(self._parse_result(r.text))

    def _parse_result(self, html_page: str) -> typing.Iterable[str]:
        soup = BeautifulSoup(html_page, "html.parser")
        for node in soup.find_all("div", class_="content"):
            del node["class"]
            self._trim_node(node)
            yield str(node).strip().replace("\n", DEF_SEP)

    def _trim_node(self, doc: bs4.Tag):
        if self._config.remove_marks:
            for node in doc("mark"):
                node.decompose()
        for node in doc("sub"):
            node.decompose()
        for node in doc("a", href=self._re_self_link):
            node["href"] = f'{SITE_URL}{node["href"]}'
        for node in doc(src=self._re_self_link):
            node["src"] = f'{SITE_URL}{node["src"]}'


# Debug
##########################################################################


def main():
    config = SimpleNamespace(
        timeout=10,
        remove_marks=False,
        dict_name=DictName.meikyou,
        search_type=SearchType.exact,
    )
    client = SakuraParisClient(typing.cast(SakuraParisConfig, config))
    print(client.fetch_def("故郷"))


if __name__ == "__main__":
    main()
