# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from japanese.helpers.common_kana import adjust_to_inflection


def test_adjust_to_inflection() -> None:
    assert adjust_to_inflection("食べた", "食べる", "たべる") == "たべた"
    assert adjust_to_inflection("食べ", "食べる", "たべる") == "たべ"
    assert adjust_to_inflection("跪いた", "跪く", "ひざまずく") == "ひざまずいた"
    assert adjust_to_inflection("跪かなかった", "跪く", "ひざまずく") == "ひざまずかなかった"
    assert adjust_to_inflection("安くなかった", "安い", "やすい") == "やすくなかった"
    assert adjust_to_inflection("繋りたい", "繋る", "つながる") == "つながりたい"
    assert adjust_to_inflection("言い方", "言い方", "いいかた") == "いいかた"
    assert adjust_to_inflection("やり遂げさせられない", "やり遂げる", "やりとげる") == "やりとげさせられない"
    assert adjust_to_inflection("死ん", "死ぬ", "しぬ") == "しん"
    assert adjust_to_inflection("たべた", "たべる", "たべる") == "たべた"
    assert adjust_to_inflection("カタカナ", "カタカナ", "かたかな") == "カタカナ"
    assert adjust_to_inflection("相合い傘", "相合い傘", "あいあいがさ") == "あいあいがさ"
    assert adjust_to_inflection("いた目", "板目", "いため") == "いため"
    assert adjust_to_inflection("軽そう", "軽装", "けいそー") == "けいそー"
    assert adjust_to_inflection("唸りました", "唸る", "うなる") == "うなりました"
    assert adjust_to_inflection("可愛くない", "可愛い", "かわいい") == "かわいくない"
    assert adjust_to_inflection("かわいくない", "可愛い", "かわいい") == "かわいくない"
    assert adjust_to_inflection("赤く", "赤い", "あかい") == "あかく"
    assert adjust_to_inflection("死ん", "死ぬ", "しぬ") == "しん"
