# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re

# Regex
RE_FLAGS = re.MULTILINE | re.IGNORECASE
RE_HTML_TAG = re.compile(r"<[^<>]+>", flags=RE_FLAGS)

# Disconnects adjacent words and renders no SVG element.
PIPE_SEPARATOR = "|"

# Same behavior as pipe, but written as punctuation.
COMMA_SEPARATORS = frozenset({",", "、"})

# Draws one trailing empty circle with no text label.
GHOST_PARTICLE = "-"

# Marks the following mora as devoiced. Indicates that the text element should be marked with a circle around the mora.
DEVOICED_PREFIX = "d"

# Makes the next connector dashed when a visible section exists before it.
TAPE_CONNECTOR = ";"

# Disconnect adjacent words and render no SVG element.
# All three are functionally identical: they produce Role.empty,
# draw no visible elements, and prevent a connecting line between words.
SEPARATORS = frozenset({PIPE_SEPARATOR, *COMMA_SEPARATORS})

# Omit these tokens from colored text output.
TEXT_HIDDEN = frozenset({PIPE_SEPARATOR, GHOST_PARTICLE})

# Break pitch-contour continuity between sections.
PITCH_BREAKS = SEPARATORS | TEXT_HIDDEN

# Affect connection logic but draw no circles.
NON_RENDERED_SECTIONS = frozenset({TAPE_CONNECTOR, *SEPARATORS})

# Small tsu (special case)
SMALL_TSU = ("っ", "ッ")
