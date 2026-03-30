# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import dataclasses
import os.path
import re
import typing

from ..helpers.consts import ADDON_NAME
from .consts import (
    AJT_JAPANESE_CSS_PATH,
    AJT_JAPANESE_JS_PATH,
    CSS_END_TOKEN,
    CSS_START_TOKEN,
    JS_SCRIPT_END,
    JS_SCRIPT_START,
)

RE_VERSION_STR = re.compile(r"AJT Japanese (?P<type>JS|CSS) (?P<version>\d+\.\d+\.\d+\.\d+)\n")
RE_JS_COMMENT = re.compile(r"\s*//.*?\n")
RE_MULTILINE_JS_CSS_COMMENT = re.compile(r"/\*.*?\*/")
RE_ANY_WHITESPACE = re.compile(r"\s+")


class FileVersionTuple(typing.NamedTuple):
    year: int
    month: int
    day: int
    patch: int


UNK_VERSION: FileVersionTuple = FileVersionTuple(0, 0, 0, 0)


class VersionedFile(typing.NamedTuple):
    version: FileVersionTuple
    text_content: str = ""

    def version_as_str(self) -> str:
        """
        Returns version as: 25.4.5.1
        """
        return ".".join(str(num) for num in self.version)


EDIT_WARN = f"/* DO NOT EDIT! This code will be overwritten by {ADDON_NAME}. */"


def wrap_bundled_js(js_code: str, version_str: str) -> str:
    return "\n".join((
        JS_SCRIPT_START,
        f"/* {ADDON_NAME} JS {version_str} */",
        EDIT_WARN,
        js_code,
        JS_SCRIPT_END,
    ))


def wrap_bundled_css(css_code: str, version_str: str) -> str:
    return "\n".join((
        CSS_START_TOKEN,
        f"/* {ADDON_NAME} CSS {version_str} */",
        EDIT_WARN,
        css_code,
        CSS_END_TOKEN,
    ))


def inline_bundled_js(vf: VersionedFile) -> str:
    js_code = re.sub(RE_JS_COMMENT, " ", vf.text_content)
    js_code = js_code.replace("\n", " ")
    js_code = re.sub(RE_MULTILINE_JS_CSS_COMMENT, " ", js_code)
    js_code = re.sub(RE_ANY_WHITESPACE, " ", js_code)
    return wrap_bundled_js(js_code.strip(), vf.version_as_str())


def inline_bundled_css(vf: VersionedFile) -> str:
    css_code = vf.text_content.replace("\n", " ")
    css_code = re.sub(RE_MULTILINE_JS_CSS_COMMENT, " ", css_code)
    css_code = re.sub(RE_ANY_WHITESPACE, " ", css_code)
    return wrap_bundled_css(css_code.strip(), vf.version_as_str())


def version_str_to_tuple(version_str: str) -> FileVersionTuple:
    return FileVersionTuple(*(int(value) for value in version_str.split(".")))


def parse_version_str(file_content: str):
    m = re.search(RE_VERSION_STR, file_content)
    if not m:
        return UNK_VERSION
    return version_str_to_tuple(m.group("version"))


def get_file_version(file_path: str) -> VersionedFile:
    try:
        with open(file_path, encoding="utf-8") as rf:
            text_content = rf.read()
        return VersionedFile(version=parse_version_str(text_content), text_content=text_content)
    except FileNotFoundError:
        pass
    return VersionedFile(UNK_VERSION)


@dataclasses.dataclass(frozen=True)
class BundledCodeFile:
    file_path: str
    version: FileVersionTuple
    import_str: str

    def version_str(self) -> str:
        return ".".join(map(str, self.version))


@dataclasses.dataclass(frozen=True)
class BundledJSFile(BundledCodeFile):
    @classmethod
    def new(cls, bundled_file_path: str):
        vf = get_file_version(bundled_file_path)
        return cls(
            file_path=bundled_file_path,
            version=vf.version,
            import_str=inline_bundled_js(vf),
        )


@dataclasses.dataclass(frozen=True)
class BundledCSSFile(BundledCodeFile):
    name_in_col: str  # legacy

    @classmethod
    def new(cls, bundled_file_path: str):
        vf = get_file_version(bundled_file_path)
        name, ext = os.path.splitext(os.path.basename(bundled_file_path))
        name_in_col = f"{name}_{vf.version_as_str()}{ext}"
        return cls(
            file_path=bundled_file_path,
            version=vf.version,
            import_str=inline_bundled_css(vf),
            name_in_col=name_in_col,  # legacy
        )

    def version_str(self) -> str:
        return ".".join(map(str, self.version))


BUNDLED_CSS_FILE = BundledCSSFile.new(AJT_JAPANESE_CSS_PATH)
BUNDLED_JS_FILE = BundledJSFile.new(AJT_JAPANESE_JS_PATH)

assert BUNDLED_JS_FILE.version != UNK_VERSION
assert BUNDLED_CSS_FILE.version != UNK_VERSION
