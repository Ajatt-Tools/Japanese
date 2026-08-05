# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Shared test helpers for SVG markup extraction and pitch accent lookup construction."""

import re
import typing
from collections.abc import Sequence

from japanese.mecab_controller import MecabController
from japanese.pitch_accents.accent_lookup import AccentLookup
from japanese.pitch_accents.colors import SvgGraphColorMode
from japanese.pitch_artist.pitch_graph import SvgPitchArtistGraphMaker
from playground.utils import NoAnkiConfigView

# The canonical test sentences.
HEADLESS_SENTENCE = """
大物[おおもの];2 ; まで;1
じんせい;1 | まで;1
じんせい;1 ; まで;a-1
つかう; , つかった;-
稼[かせ]いで;k2. がっこう;
がっこう;1. つくった;2.
君[dきdみ]; dの 嘘[dうdそ];1 dを.
自分[じぶん]; じゃ | できない;k2.
ひとり;1-
ひとり;2-
ひとり;3-
よねん; ぐらい;pa
よねん; ぐらい;po1
"""

NUM_EXPECTED_SEQUENCES = 15

RE_GROUP_CLASS: typing.Final = re.compile(r'<g class="(?P<class_name>[^"]+)">')
RE_CIRCLE_POSITION: typing.Final = re.compile(r'cx="(?P<cx>[0-9.]+)" cy="(?P<cy>[0-9.]+)"')
RE_TEXT_LABEL: typing.Final = re.compile(r"<text[^>]*>(?P<label>[^<]*)</text>")
RE_SVG_ROOT_DIMENSIONS: typing.Final = re.compile(
    r'viewBox="0 0 (?P<view_box_width>\d+) (?P<view_box_height>\d+)" height="(?P<visible_height>\d+)px"'
)


class CirclePosition(typing.NamedTuple):
    """Integer circle center coordinates in SVG user units."""

    x: int
    y: int


class SvgRootDimensions(typing.NamedTuple):
    """Integer dimensions declared on the root SVG element."""

    view_box_width: int
    view_box_height: int
    visible_height: int


def extract_group_class_names(svg: str) -> Sequence[str]:
    """Extract CSS class names from all SVG group elements."""
    return [match.group("class_name") for match in RE_GROUP_CLASS.finditer(svg)]


def make_accent_lookup(cfg: NoAnkiConfigView) -> AccentLookup:
    """Create an AccentLookup with a quiet MeCab controller for tests."""
    return AccentLookup(cfg, MecabController(verbose=False, cache_max_size=cfg.cache_lookups))


def make_fresh_config() -> NoAnkiConfigView:
    """Return a config that is not shared with the session fixture, so it is safe to mutate."""
    return NoAnkiConfigView()


def make_svg_attributes_config() -> NoAnkiConfigView:
    """Return a fresh config with SVG attributes color mode enabled."""
    cfg = make_fresh_config()
    cfg.svg_graphs["color_mode"] = SvgGraphColorMode.svg_attributes.name
    return cfg


def render_first_graph(cfg: NoAnkiConfigView, notation: str) -> str:
    """Render the first Pitch Artist graph for a notation string."""
    gen = SvgPitchArtistGraphMaker(cfg)
    return list(gen.make_graphs(gen.make_sequences(notation)))[0]


def extract_circles(svg: str) -> list[CirclePosition]:
    """Extract (x, y) integer pairs from all <circle> elements in the SVG."""
    return [
        CirclePosition(x=int(float(match.group("cx"))), y=int(float(match.group("cy"))))
        for match in RE_CIRCLE_POSITION.finditer(svg)
    ]


def extract_text_labels(svg: str) -> list[str]:
    """Extract text content from all <text> elements in the SVG."""
    return [match.group("label") for match in RE_TEXT_LABEL.finditer(svg)]


def extract_svg_root_dimensions(svg: str) -> SvgRootDimensions:
    """Extract integer root SVG dimensions from viewBox and height attributes."""
    match = RE_SVG_ROOT_DIMENSIONS.search(svg)
    assert match is not None, "integer root SVG dimensions not found"
    return SvgRootDimensions(
        view_box_width=int(match.group("view_box_width")),
        view_box_height=int(match.group("view_box_height")),
        visible_height=int(match.group("visible_height")),
    )


def extract_visible_height(svg: str) -> int:
    """Extract the visible height (in pixels) from the SVG root element."""
    return extract_svg_root_dimensions(svg).visible_height
