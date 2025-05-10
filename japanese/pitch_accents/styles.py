# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum


@enum.unique
class HTMLPitchPatternStyle(enum.Enum):
    """
    Styles for HTML pitch patterns.
    """

    u_biq = enum.auto()
    u_biq_color_coded = enum.auto()
    javdejong = enum.auto()
    kanjium = enum.auto()
    none = enum.auto()


class XmlTags:
    # low accent, underline ___
    low_start = "<low>"
    low_end = "</low>"
    # low accent, rising _/
    low_rise_start = "<low_rise>"
    low_rise_end = "</low_rise>"
    # high accent, overline ‾‾‾
    high_start = "<high>"
    high_end = "</high>"
    # high accent, going down ‾‾‾\
    high_drop_start = "<high_drop>"
    high_drop_end = "</high_drop>"  # &#42780; (ꜜ)
    # Devoiced, e.g. シュ (NHK data only)
    devoiced_start = "<devoiced>"
    devoiced_end = "</devoiced>"
    # Nasal, e.g. コ° (NHK data only)
    nasal_start = "<nasal>"
    nasal_end = "</nasal>"
    # Nasal mark (NHK data only). It should be added after the nasal kana character (e.g. '°' in コ°).
    handakuten_start = "<handakuten>"  # &#176; (°), colored red.
    handakuten_end = "</handakuten>"


PITCH_COLOR_PLACEHOLDER = "[PITCH_COLOR]"
STYLE_MAP: dict[HTMLPitchPatternStyle, dict[str, str]] = dict()

# javdejong: style used in the original Japanese Pitch Accent Anki add-on.
# Low accents aren't marked, high accents are marked with an overline.
STYLE_MAP[HTMLPitchPatternStyle.javdejong] = {
    # low
    XmlTags.low_start: "",
    XmlTags.low_end: "",
    # low, rise at the end
    XmlTags.low_rise_start: "",
    XmlTags.low_rise_end: "",
    # high
    XmlTags.high_start: '<span style="text-decoration:overline;">',
    XmlTags.high_end: "</span>",
    # high, drop at the end
    XmlTags.high_drop_start: '<span style="text-decoration:overline;">',
    XmlTags.high_drop_end: "</span>&#42780;",  # down arrow at the end
    # nasal, e.g. カ゚
    XmlTags.nasal_start: "",
    XmlTags.nasal_end: "",
    # handakuten (°)
    XmlTags.handakuten_start: '<span style="color: red;">',
    XmlTags.handakuten_end: "</span>",
    # devoiced
    XmlTags.devoiced_start: '<span style="color: royalblue;">',
    XmlTags.devoiced_end: "</span>",
}

# u-biq: style used on the u-biq website, https://accent.u-biq.org/
# This version has color-coded lines.
STYLE_MAP[HTMLPitchPatternStyle.u_biq_color_coded] = {
    **STYLE_MAP[HTMLPitchPatternStyle.javdejong],
    # low
    XmlTags.low_start: f'<span style="box-shadow: inset 0px -2px 0 0px {PITCH_COLOR_PLACEHOLDER};">',
    XmlTags.low_end: "</span>",
    # low, rise at the end
    XmlTags.low_rise_start: f'<span style="box-shadow: inset -2px -2px 0 0 {PITCH_COLOR_PLACEHOLDER};">',
    XmlTags.low_rise_end: "</span>",
    # high
    XmlTags.high_start: f'<span style="box-shadow: inset 0px 2px 0 0px {PITCH_COLOR_PLACEHOLDER};">',
    XmlTags.high_end: "</span>",
    # high, drop at the end
    XmlTags.high_drop_start: f'<span style="box-shadow: inset -2px 2px 0 0px {PITCH_COLOR_PLACEHOLDER};">',
    XmlTags.high_drop_end: "</span>",
}

# u-biq: style used on the u-biq website, https://accent.u-biq.org/
# This version has orange lines (like the original).
STYLE_MAP[HTMLPitchPatternStyle.u_biq] = {
    k: v.replace(PITCH_COLOR_PLACEHOLDER, "#FF6633")
    for k, v in STYLE_MAP[HTMLPitchPatternStyle.u_biq_color_coded].items()
}

# kanjium: style which is part of the kanjium project https://github.com/mifunetoshiro/kanjium
STYLE_MAP[HTMLPitchPatternStyle.kanjium] = {
    **STYLE_MAP[HTMLPitchPatternStyle.javdejong],
    # low
    XmlTags.low_start: "",
    XmlTags.low_end: "",
    # low, rise at the end
    XmlTags.low_rise_start: "",
    XmlTags.low_rise_end: "",
    # high
    XmlTags.high_start: '<span style="display:inline-block;position:relative;"><span style="display:inline;">',
    XmlTags.high_end: (
        "</span><span"
        ' style="border-color:currentColor;display:block;user-select:none;pointer-events:none;position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;border-top-style:solid;"></span></span>'
    ),
    # high, drop at the end
    XmlTags.high_drop_start: (
        '<span style="display:inline-block;position:relative;padding-right:0.1em;margin-right:0.1em;"><span'
        ' style="display:inline;">'
    ),
    XmlTags.high_drop_end: (
        "</span><span"
        ' style="border-color:currentColor;display:block;user-select:none;pointer-events:none;position:absolute;top:0.1em;left:0;right:0;height:0;border-top-width:0.1em;border-top-style:solid;right:-0.1em;height:0.4em;border-right-width:0.1em;border-right-style:solid;"></span></span>'
    ),
}

# none: use class names.
# The user can configure their own styles in the Styling section of the card template.
STYLE_MAP[HTMLPitchPatternStyle.none] = {
    # low
    XmlTags.low_start: '<span class="low">',
    XmlTags.low_end: "</span>",
    # low, rise at the end
    XmlTags.low_rise_start: '<span class="low_rise">',
    XmlTags.low_rise_end: "</span>",
    # high
    XmlTags.high_start: '<span class="high">',
    XmlTags.high_end: "</span>",
    # high, drop at the end
    XmlTags.high_drop_start: '<span class="high_drop">',
    XmlTags.high_drop_end: "</span>",
    # nasal, e.g. カ゚
    XmlTags.nasal_start: '<span class="nasal">',
    XmlTags.nasal_end: "</span>",
    # handakuten (°)
    XmlTags.handakuten_start: '<span class="handakuten">',
    XmlTags.handakuten_end: "</span>",
    # devoiced
    XmlTags.devoiced_start: '<span class="devoiced">',
    XmlTags.devoiced_end: "</span>",
}
