# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import io

from ..mecab_controller.kana_conv import to_katakana

HALF_WIDTH_KATAKANA_MAPPING = {
    "ァ": "ｧ",
    "ア": "ｱ",
    "ィ": "ｨ",
    "イ": "ｲ",
    "ゥ": "ｩ",
    "ウ": "ｳ",
    "ェ": "ｪ",
    "エ": "ｴ",
    "ォ": "ｫ",
    "オ": "ｵ",
    "カ": "ｶ",
    "ガ": "ｶﾞ",
    "キ": "ｷ",
    "ギ": "ｷﾞ",
    "ク": "ｸ",
    "グ": "ｸﾞ",
    "ケ": "ｹ",
    "ゲ": "ｹﾞ",
    "コ": "ｺ",
    "ゴ": "ｺﾞ",
    "サ": "ｻ",
    "ザ": "ｻﾞ",
    "シ": "ｼ",
    "ジ": "ｼﾞ",
    "ス": "ｽ",
    "ズ": "ｽﾞ",
    "セ": "ｾ",
    "ゼ": "ｾﾞ",
    "ソ": "ｿ",
    "ゾ": "ｿﾞ",
    "タ": "ﾀ",
    "ダ": "ﾀﾞ",
    "チ": "ﾁ",
    "ヂ": "ﾁﾞ",
    "ッ": "ｯ",
    "ツ": "ﾂ",
    "ヅ": "ﾂﾞ",
    "テ": "ﾃ",
    "デ": "ﾃﾞ",
    "ト": "ﾄ",
    "ド": "ﾄﾞ",
    "ナ": "ﾅ",
    "ニ": "ﾆ",
    "ヌ": "ﾇ",
    "ネ": "ﾈ",
    "ノ": "ﾉ",
    "ハ": "ﾊ",
    "バ": "ﾊﾞ",
    "パ": "ﾊﾟ",
    "ヒ": "ﾋ",
    "ビ": "ﾋﾞ",
    "ピ": "ﾋﾟ",
    "フ": "ﾌ",
    "ブ": "ﾌﾞ",
    "プ": "ﾌﾟ",
    "ヘ": "ﾍ",
    "ベ": "ﾍﾞ",
    "ペ": "ﾍﾟ",
    "ホ": "ﾎ",
    "ボ": "ﾎﾞ",
    "ポ": "ﾎﾟ",
    "マ": "ﾏ",
    "ミ": "ﾐ",
    "ム": "ﾑ",
    "メ": "ﾒ",
    "モ": "ﾓ",
    "ャ": "ｬ",
    "ヤ": "ﾔ",
    "ュ": "ｭ",
    "ユ": "ﾕ",
    "ョ": "ｮ",
    "ヨ": "ﾖ",
    "ラ": "ﾗ",
    "リ": "ﾘ",
    "ル": "ﾙ",
    "レ": "ﾚ",
    "ロ": "ﾛ",
    "ワ": "ﾜ",
    "ヲ": "ｦ",
    "ン": "ﾝ",
    "ヴ": "ｳﾞ",
    "ヷ": "ﾜﾞ",
    "ヺ": "ｦﾞ",
    "ー": "ｰ",
    # "ヮ":,
    # "ヰ":,
    # "ヱ":,
    # "ヵ":,
    # "ヶ":,
    # "ヸ":,
    # "ヹ":,
}


def to_half_width_katakana(s: str) -> str:
    buffer = io.StringIO()
    for char in to_katakana(s):
        buffer.write(HALF_WIDTH_KATAKANA_MAPPING.get(char, char))
    return buffer.getvalue()
