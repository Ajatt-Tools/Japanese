# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.audio_manager.source_manager import normalize_filename


def test_normalize_filename() -> None:
    assert normalize_filename("スズキ目の海魚。全長約10センチメートル。") == "スズキ目の海魚。全長約10センチメートル。"
    assert normalize_filename("地獄[じごく]") == "地獄_じごく"
