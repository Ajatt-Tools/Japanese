# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import dataclasses
import os
from collections.abc import Iterable

try:
    from .audio_manager import FileUrlData
except ImportError:
    from audio_manager import FileUrlData


def ensure_unique_urls(files: Iterable[FileUrlData]) -> Iterable[FileUrlData]:
    """
    Ensure there are no duplicate URLs.
    They can be present if one word appeared in the source text more than once.
    """
    return {item.url: item for item in files}.values()


def ensure_unique_names(files: Iterable[FileUrlData]) -> Iterable[FileUrlData]:
    """
    Ensure that the desired filenames are unique.
    Normally, word+reading+accent distinguishes a file with 100% certainty,
    but some audio sources lack accent data.
    """
    unique_names = {}
    for file in files:
        name, ext = os.path.splitext(file.desired_filename)
        idx = 1
        while file.desired_filename in unique_names:
            file = dataclasses.replace(file, desired_filename=f"{name}({idx}){ext}")
            idx += 1
        unique_names[file.desired_filename] = file
    return unique_names.values()


def ensure_unique_files(files: Iterable[FileUrlData]) -> Iterable[FileUrlData]:
    """
    Ensure that the URLs are not repeated and that the desired filenames are unique.
    """
    return ensure_unique_names(ensure_unique_urls(files))


# Debug
##########################################################################


def main():
    examples = [
        FileUrlData("/mnt/data/file1.png", "file1.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file1.png", "file2.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file1.png", "file1.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file2.png", "file2.png", "単語", "NHK"),
        FileUrlData("/mnt/data/file2.png", "file1.png", "単語", "NHK"),
    ]
    for file in ensure_unique_files(examples):
        print(file)


if __name__ == '__main__':
    main()
