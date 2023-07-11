# Copyright: Ren Tatsumoto <tatsu at autistici.org> and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import enum


@enum.unique
class PitchPatternStyle(enum.Enum):
    javdejong = enum.auto()
    u_biq = enum.auto()
    none = enum.auto()


class XmlTags:
    # low accent, underline ___
    low_start = '<low>'
    low_end = '</low>'
    # low accent, rising _/
    low_rise_start = '<low_rise>'
    low_rise_end = '</low_rise>'
    # high accent, overline ‾‾‾
    high_start = '<high>'
    high_end = '</high>'
    # high accent, going down ‾‾‾\
    high_drop_start = '<high_drop>'
    high_drop_end = '</high_drop>'  # &#42780; (ꜜ)
    # NHK data only:
    nasal_start = '<nasal>'  # Red color &#176; (°)
    nasal_end = '</nasal>'
    devoiced_start = '<devoiced>'
    devoiced_end = '</devoiced>'


STYLE_MAP = {
    PitchPatternStyle.javdejong: {
        # Style used in the original Japanese Pitch Accent Anki add-on.
        # Low accents aren't marked, high accents are marked with an overline.

        # low
        XmlTags.low_start: '',
        XmlTags.low_end: '',
        # low, rise at the end
        XmlTags.low_rise_start: '',
        XmlTags.low_rise_end: '',
        # high
        XmlTags.high_start: '<span style="text-decoration:overline;">',
        XmlTags.high_end: '</span>',
        # high, drop at the end
        XmlTags.high_drop_start: '<span style="text-decoration:overline;">',
        XmlTags.high_drop_end: '</span>&#42780;',  # down arrow at the end
        # nasal, e.g. カ゚
        XmlTags.nasal_start: '<span style="color: red;">',
        XmlTags.nasal_end: '</span>',
        # devoiced
        XmlTags.devoiced_start: '<span style="color: royalblue;">',
        XmlTags.devoiced_end: '</span>',
    },
    PitchPatternStyle.u_biq: {
        # Style used on the u-biq website, https://accent.u-biq.org/

        # low
        XmlTags.low_start: '<span style="box-shadow: inset 0px -2px 0 0px #FF6633;">',
        XmlTags.low_end: '</span>',
        # low, rise at the end
        XmlTags.low_rise_start: '<span style="box-shadow: inset -2px -2px 0 0 #FF6633;">',
        XmlTags.low_rise_end: '</span>',
        # high
        XmlTags.high_start: '<span style="box-shadow: inset 0px 2px 0 0px #FF6633;">',
        XmlTags.high_end: '</span>',
        # high, drop at the end
        XmlTags.high_drop_start: '<span style="box-shadow: inset -2px 2px 0 0px #FF6633;">',
        XmlTags.high_drop_end: '</span>',
        # nasal, e.g. カ゚
        XmlTags.nasal_start: '<span style="color: red;">',
        XmlTags.nasal_end: '</span>',
        # devoiced
        XmlTags.devoiced_start: '<span style="color: royalblue;">',
        XmlTags.devoiced_end: '</span>',
    },
    PitchPatternStyle.none: {
        # Use class names.
        # The user can configure their own styles in the Styling section of the card type.

        # low
        XmlTags.low_start: '<span class="low">',
        XmlTags.low_end: '</span>',
        # low, rise at the end
        XmlTags.low_rise_start: '<span class="low_rise">',
        XmlTags.low_rise_end: '</span>',
        # high
        XmlTags.high_start: '<span class="high">',
        XmlTags.high_end: '</span>',
        # high, drop at the end
        XmlTags.high_drop_start: '<span class="high_drop">',
        XmlTags.high_drop_end: '</span>',
        # nasal, e.g. カ゚
        XmlTags.nasal_start: '<span class="nasal">',
        XmlTags.nasal_end: '</span>',
        # devoiced
        XmlTags.devoiced_start: '<span class="devoiced">',
        XmlTags.devoiced_end: '</span>',
    }
}

