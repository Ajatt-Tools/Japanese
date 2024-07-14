# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
import re
import typing

from .consts import AJT_JAPANESE_CSS_PATH, AJT_JAPANESE_JS_PATH

RE_VERSION_STR = re.compile(r"AJT Japanese (?P<type>JS|CSS) (?P<version>\d+\.\d+\.\d+\.\d+)\n")
FileVersionTuple = tuple[int, int, int, int]
UNK_VERSION: FileVersionTuple = 0, 0, 0, 0


class VersionedFile(typing.NamedTuple):
    version: FileVersionTuple
    text_content: str = ""

    def version_as_str(self) -> str:
        return '.'.join(str(num) for num in self.version)


def parse_version_str(file_content: str):
    m = re.search(RE_VERSION_STR, file_content)
    if not m:
        return UNK_VERSION
    return tuple(int(value) for value in m.group("version").split("."))


def get_file_version(file_path: str) -> VersionedFile:
    try:
        with open(file_path, encoding="utf-8") as rf:
            text_content = rf.read()
        return VersionedFile(version=parse_version_str(text_content), text_content=text_content)
    except FileNotFoundError:
        pass
    return VersionedFile(UNK_VERSION)



def import_str_from_name(name_in_col: str, ftype: str) -> str:
    if ftype == "css":
        return f'@import url("{name_in_col}");'
    elif ftype == "js":
        return f'<script defer src="{name_in_col}"></script>'
    raise RuntimeError("unreachable.")


class BundledNoteTypeSupportFile(typing.NamedTuple):
    file_path: str
    version: FileVersionTuple
    name_in_col: str
    import_str: str

    def path_in_col(self) -> str:
        from aqt import mw

        assert mw, "Function can run only when anki is running."
        return os.path.join(mw.col.media.dir(), self.name_in_col)

    @classmethod
    def new(cls, bundled_file_path: str, ftype: str):
        vf = get_file_version(bundled_file_path)
        name, ext = os.path.splitext(os.path.basename(bundled_file_path))
        name_in_col = f"{name}_{vf.version_as_str()}{ext}"
        return cls(
            file_path=bundled_file_path,
            version=vf.version,
            name_in_col=name_in_col,
            import_str=import_str_from_name(name_in_col, ftype=ftype),
        )


BUNDLED_JS_FILE = BundledNoteTypeSupportFile.new(AJT_JAPANESE_JS_PATH, ftype="js")
BUNDLED_CSS_FILE = BundledNoteTypeSupportFile.new(AJT_JAPANESE_CSS_PATH, ftype="css")

assert BUNDLED_JS_FILE.version != UNK_VERSION
assert BUNDLED_CSS_FILE.version != UNK_VERSION
