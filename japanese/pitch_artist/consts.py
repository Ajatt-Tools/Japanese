# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

RE_FLAGS = re.MULTILINE | re.IGNORECASE

# A special symbol reserved for drawing empty trailing circles.
GHOST_PARTICLE = "-"

# Indicates that the previous mora and the next mora should be connected with a dotted line.
TAPE_CONNECTOR = ";"

# Indicates that the text element should be marked with a circle around the mora.
DEVOICED_PREFIX = "d"

# Characters that disconnect adjacent words in a pitch expression.
# All three are functionally identical: they produce Role.empty,
# draw no visible elements, and prevent a connecting line between words.
SEPARATORS = {"|", ",", "、"}

TEXT_HIDDEN = {"|", GHOST_PARTICLE}

# All characters that break the pitch contour: separators, ghost particle, and commas.
PITCH_BREAKS = {*TEXT_HIDDEN, ",", "、"}

ALL_HIDDEN = {TAPE_CONNECTOR, *SEPARATORS}
