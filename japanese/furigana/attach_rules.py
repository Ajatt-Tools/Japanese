# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from ..mecab_controller.basic_types import PartOfSpeech

SKIP_COLORING = frozenset(
    (
        PartOfSpeech.other,
        PartOfSpeech.filler,
        PartOfSpeech.particle,
        PartOfSpeech.symbol,
    )
)

NEVER_ATTACH = frozenset("ない,なぁ,とか,けど,だけ,だろ,でしょ,なる,は,が,の,しまう,おる".split(","))
