# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
"""Shared test helpers for SVG markup extraction and pitch accent lookup construction."""

import re
from collections.abc import Sequence

from japanese.mecab_controller import MecabController
from japanese.pitch_accents.accent_lookup import AccentLookup
from playground.utils import NoAnkiConfigView

RE_GROUP_CLASS = re.compile(r'<g class="(?P<class_name>[^"]+)">')


def extract_group_class_names(svg: str) -> Sequence[str]:
    """Extract CSS class names from all SVG group elements."""
    return [match.group("class_name") for match in RE_GROUP_CLASS.finditer(svg)]


def make_accent_lookup(cfg: NoAnkiConfigView) -> AccentLookup:
    """Create an AccentLookup with a quiet MeCab controller for tests."""
    return AccentLookup(cfg, MecabController(verbose=False, cache_max_size=cfg.cache_lookups))


def make_fresh_config() -> NoAnkiConfigView:
    """Return a config that is not shared with the session fixture, so it is safe to mutate."""
    return NoAnkiConfigView()
