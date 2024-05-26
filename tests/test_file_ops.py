# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os.path

from japanese.helpers.file_ops import find_config_json, user_files_dir


def test_config_json():
    assert os.path.isfile(find_config_json())


def test_user_files_dir():
    assert os.path.isdir(user_files_dir())
