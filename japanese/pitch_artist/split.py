# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from typing import NamedTuple

RE_FLAGS = re.MULTILINE | re.IGNORECASE
GHOST_PARTICLE = "-"  # A special symbol reserved for drawing empty trailing circles.
DEVOICED_PREFIX = "d"
# Characters that disconnect adjacent words in a pitch expression.
# All three are functionally identical: they produce Role.empty,
# draw no visible elements, and prevent a connecting line between words.
SEPARATORS = ["|", ",", "、"]
# The ghost particle is similar to a separator but draws an empty trailing circle.
SENT_HIDDEN = ["|", GHOST_PARTICLE]
# All characters that break the pitch contour: separators, ghost particle, and commas.
PITCH_BREAKS = SENT_HIDDEN + [",", "、"]


def split_multiple_pitch_notations(sequences: list[list[str]]) -> list[list[str]]:
    """Expand sections that contain comma-separated pitch notations into separate sequences.

    For example, a section like "word;1,2" is split into two sequences,
    one with "word;1" and one with "word;2", each carrying the same trailing sections.
    """
    result = []
    for sequence in sequences:
        first_section = split_section(sequence[0])
        if first_section.sep:
            for accent in first_section.accent.split(","):
                result.append([f"{first_section.word};{accent}"] + sequence[1:])
        else:
            result.append(sequence)

    return result


def normalize_for_parsing(expr: str) -> str:
    """Normalize a pitch expression string for parsing by inserting whitespace delimiters.

    Takes advantage of the fact that Japanese does not use spaces.
    Strips HTML tags, splits on punctuation, and normalizes commas.
    """
    # Using spaces to separate everything.
    # Taking advantage of the fact that Japanese doesn't use spaces.
    expr = expr.replace("<br>", " . ")
    try:
        # Import kept inside function: `html_to_text_line` may raise AttributeError
        # on older Anki versions, and the except branch provides a regex fallback.
        from anki.utils import html_to_text_line

        expr = html_to_text_line(expr)
    except AttributeError:
        expr = re.sub(r"<[^<>]+>", "", expr, flags=RE_FLAGS)
    expr = re.sub(r"([。!?！？])", r" \g<1> .", expr, flags=RE_FLAGS)
    expr = re.sub(r"([「」|、､])", r" \g<1> ", expr, flags=RE_FLAGS)
    expr = re.sub(r"([^ ]), ", r" \g<1> , ", expr, flags=RE_FLAGS)
    return expr


def split_to_sentences(expr: str) -> list[str]:
    """Split a normalized expression into individual sentences on periods and newlines."""
    return list(filter(bool, map(str.strip, re.split(r"[.\n]+", expr, flags=RE_FLAGS))))


def split_to_sections(sentence: str) -> list[str]:
    """Split a sentence into whitespace-delimited sections."""
    return [s for s in re.split(r"[\n\t\s　]+", sentence, flags=RE_FLAGS) if s]


def detach_ghost_particle(text: str) -> str:
    """Ensure a trailing ghost particle is separated by a space and followed by end-of-string.

    After a ghost particle there has to be the end of the sentence,
    which is ensured by adding an extra dot.
    """
    return re.sub(rf"{GHOST_PARTICLE}[\s\n.]*$", f" {GHOST_PARTICLE}", text)


def furigana_to_reading(word: str) -> str:
    """Strip furigana bracket notation, returning only the reading portion."""
    return re.sub(r"([^\[\]]*\[|])", "", word, flags=RE_FLAGS)


def filter_kana(reading: str) -> str:
    """Remove all non-kana characters from a reading string, preserving devoiced and ghost markers."""
    return re.sub(rf"[^ぁ-ゔゞァ-・ヽヾ゛゜ぁ-んァ-ンー{DEVOICED_PREFIX}{GHOST_PARTICLE}]", "", reading, flags=RE_FLAGS)


def kana_to_moras(kana: str) -> list[str]:
    """Split a kana string into a list of morae, respecting combination characters."""
    return re.findall(rf"{DEVOICED_PREFIX}?.[ァィゥェォャュョぁぃぅぇぉゃゅょ]?", kana, flags=RE_FLAGS)


class DevoicedMora(str):
    """A string subclass that marks a mora as devoiced for rendering purposes."""


def split_to_moras(reading: str) -> list[str]:
    """Convert a reading string into a list of morae, wrapping devoiced morae in DevoicedMora."""
    kana = filter_kana(reading)
    moras = kana_to_moras(kana)
    return [
        mora if not mora.startswith(DEVOICED_PREFIX) else DevoicedMora(mora[len(DEVOICED_PREFIX) :]) for mora in moras
    ]


class SectionParts(NamedTuple):
    """Parsed components of a raw section string: word, separator, and accent string."""

    word: str
    sep: str | None
    accent: str


RE_SECTION = re.compile(r"^(?P<word>[^；;:]+)(?P<sep>[；;:])?(?P<accent>.*)$", flags=RE_FLAGS)


def split_section(raw_section: str) -> SectionParts:
    """Parse a raw section string into a SectionParts.

    The section format is "word[;:]accent". If no separator is found,
    'sep' is empty and 'accent' is empty.
    """
    m = re.match(RE_SECTION, raw_section)
    if m:
        return SectionParts(
            word=m.group("word"),
            sep=m.group("sep"),
            accent=m.group("accent"),
        )
    else:
        return SectionParts(
            word=raw_section,
            sep="",
            accent="",
        )


class SplitAccent(NamedTuple):
    """Parsed pitch accent properties: particle marker, role, pitch number, keihan levels."""

    is_particle: str | None
    role: str | None
    pitch: str | None
    levels: str | None
    keihan: bool


RE_SPLIT_ACCENT = re.compile(r"^(?P<is_particle>p)?(?P<role>[a-zA-Z])?(?P<pitch>-?\d)?$", flags=RE_FLAGS)
RE_SPLIT_ACCENT_KEIHAN = re.compile(r"^(?P<is_particle>p)?(?P<role>[a-zA-Z])?(?P<pitch>-?\d)?$", flags=RE_FLAGS)


def split_accent(raw_accent: str) -> SplitAccent:
    """Parse a raw accent string into a SplitAccent describing pitch accent properties.

    For Tokyo dialect, returns 'is_particle', 'role', and 'pitch'.
    For Keihan dialect, returns 'role', 'levels', and 'keihan=True'.
    Falls back to all-None with 'keihan=False' for unrecognized input.
    """
    # any group can be none
    m = re.match(RE_SPLIT_ACCENT, raw_accent)
    if m:
        return SplitAccent(
            is_particle=m.group("is_particle"),
            role=m.group("role") or m.group("is_particle"),  # p1 would really mean pp1, etc.
            pitch=m.group("pitch"),
            keihan=False,
            levels=None,
        )

    m = re.match(r"^(?P<role>[a-zA-Z]{1,2})[；;](?P<levels>[hlHL]+)$", raw_accent, flags=RE_FLAGS)
    if m:
        return SplitAccent(
            is_particle=None,
            role=m.group("role"),
            pitch=None,
            levels=m.group("levels"),
            keihan=True,
        )

    return SplitAccent(
        is_particle=None,
        role=None,
        pitch=None,
        levels=None,
        keihan=False,
    )
