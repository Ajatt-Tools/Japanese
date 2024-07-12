# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import os.path
import re
import typing

from .consts import AJT_JAPANESE_CSS_PATH, AJT_JAPANESE_JS_PATH

RE_VERSION_STR = re.compile(r"AJT Japanese (?P<type>JS|CSS) (?P<version>\d+\.\d+\.\d+\.\d+)\n")
FileVersion = tuple[int, int, int, int]
UNK_VERSION: FileVersion = 0, 0, 0, 0


def parse_version_str(file_content: str):
    m = re.search(RE_VERSION_STR, file_content)
    if not m:
        return UNK_VERSION
    return tuple(int(value) for value in m.group("version").split("."))


def get_file_version(file_path) -> FileVersion:
    try:
        with open(file_path, encoding="utf-8") as rf:
            return parse_version_str(rf.read())
    except FileNotFoundError:
        pass
    return UNK_VERSION


def import_str_from_name(name_in_col: str, ftype: str) -> str:
    if ftype == "css":
        return f'@import url("{name_in_col}");'
    elif ftype == "js":
        return f'<script defer src="{name_in_col}"></script>'
    raise RuntimeError("unreachable.")


class BundledNoteTypeSupportFile(typing.NamedTuple):
    file_path: str
    version: FileVersion
    name_in_col: str
    import_str: str

    def path_in_col(self) -> str:
        from aqt import mw

        assert mw, "Function can run only when anki is running."
        return os.path.join(mw.col.media.dir(), self.name_in_col)

    @classmethod
    def new(cls, bundled_file_path: str, ftype: str):
        version = get_file_version(bundled_file_path)
        name, ext = os.path.splitext(os.path.basename(bundled_file_path))
        name_in_col = f"{name}_{'.'.join(str(num) for num in version)}{ext}"
        return cls(
            file_path=bundled_file_path,
            version=version,
            name_in_col=name_in_col,
            import_str=import_str_from_name(name_in_col, ftype=ftype),
        )


BUNDLED_JS_FILE = BundledNoteTypeSupportFile.new(AJT_JAPANESE_JS_PATH, ftype="js")
BUNDLED_CSS_FILE = BundledNoteTypeSupportFile.new(AJT_JAPANESE_CSS_PATH, ftype="css")

assert BUNDLED_JS_FILE.version != UNK_VERSION
assert BUNDLED_CSS_FILE.version != UNK_VERSION
