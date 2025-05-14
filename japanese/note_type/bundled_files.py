# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
import re
import typing

from ..helpers.consts import ADDON_NAME
from .consts import AJT_JAPANESE_CSS_PATH, AJT_JAPANESE_JS_PATH

RE_VERSION_STR = re.compile(r"AJT Japanese (?P<type>JS|CSS) (?P<version>\d+\.\d+\.\d+\.\d+)\n")
RE_JS_COMMENT = re.compile(r"\s*//.*?\n")
RE_MULTILINE_JS_COMMENT = re.compile(r"/\*.*?\*/")
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


def wrap_bundled_js(js_text: str, version_str: str) -> str:
    return f"<script>\n/* {ADDON_NAME} JS {version_str} */\n{EDIT_WARN}\n{js_text}\n</script>"


def inline_bundled_js(vf: VersionedFile) -> str:
    js_text = re.sub(RE_JS_COMMENT, " ", vf.text_content)
    js_text = js_text.replace("\n", " ")
    js_text = re.sub(RE_MULTILINE_JS_COMMENT, " ", js_text)
    js_text = re.sub(RE_ANY_WHITESPACE, " ", js_text)
    return wrap_bundled_js(js_text.strip(), vf.version_as_str())


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


class BundledCSSFile(typing.NamedTuple):
    file_path: str
    version: FileVersionTuple
    import_str: str
    text_content: str
    name_in_col: str

    def path_in_col(self) -> str:
        from aqt import mw

        assert mw, "Function can run only when anki is running."
        return os.path.join(mw.col.media.dir(), self.name_in_col)

    @classmethod
    def new(cls, bundled_file_path: str):
        vf = get_file_version(bundled_file_path)
        name, ext = os.path.splitext(os.path.basename(bundled_file_path))
        name_in_col = f"{name}_{vf.version_as_str()}{ext}"
        return cls(
            file_path=bundled_file_path,
            version=vf.version,
            name_in_col=name_in_col,
            import_str=f'@import url("{name_in_col}");',
            text_content=vf.text_content,
        )

    def version_str(self) -> str:
        return ".".join(map(str, self.version))


class BundledJSFile(typing.NamedTuple):
    file_path: str
    version: FileVersionTuple
    import_str: str

    @classmethod
    def new(cls, bundled_file_path: str):
        vf = get_file_version(bundled_file_path)
        return cls(
            file_path=bundled_file_path,
            version=vf.version,
            import_str=inline_bundled_js(vf),
        )

    def version_str(self) -> str:
        return ".".join(map(str, self.version))


BUNDLED_CSS_FILE = BundledCSSFile.new(AJT_JAPANESE_CSS_PATH)
BUNDLED_JS_FILE = BundledJSFile.new(AJT_JAPANESE_JS_PATH)

assert BUNDLED_JS_FILE.version != UNK_VERSION
assert BUNDLED_CSS_FILE.version != UNK_VERSION
