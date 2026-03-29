# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import collections
import io
from typing import Optional, Union

from ..config_view import JapaneseConfig
from ..helpers.profiles import ColorCodePitchFormat
from ..pitch_accents.basic_types import (
    AccDbParsedToken,
    PitchType,
    PitchUnknown,
    adjust_if_kifuku,
)
from .attach_rules import SKIP_COLORING


def should_skip_coloring(token: AccDbParsedToken) -> bool:
    """
    Don't color special symbols and words without known pitch.
    Note: particles don't have their own pitch accent.
    The pitch of a particle is determined by the accent type of the word it follows.
    """
    return token.part_of_speech in SKIP_COLORING or not token.has_pitch()


def guess_main_pitch_type(token: AccDbParsedToken) -> Union[PitchType, PitchUnknown]:
    pitch_types = collections.Counter(accent.type for entry in token.headword_accents for accent in entry.pitches)
    if len(pitch_types) == 1:
        # return the most common pitch (the first).
        return pitch_types.most_common(1)[0][0]
    elif len(pitch_types) > 1:
        # many pitch accents for one word
        return PitchUnknown.many
    else:
        # no pitch accent at all
        return PitchUnknown.none


class ColorCodeWrapper(io.StringIO):
    _token: AccDbParsedToken
    _output_format: ColorCodePitchFormat
    _coloring_enabled: bool = True
    _cfg: JapaneseConfig

    def __init__(self, token: AccDbParsedToken, output_format: ColorCodePitchFormat, cfg: JapaneseConfig) -> None:
        super().__init__()
        self._cfg = cfg
        self._token = token
        self._output_format = output_format
        self._set_coloring()
        if self._coloring_enabled:
            self._start_wrap()

    def _set_coloring(self) -> None:
        assert isinstance(self._output_format, ColorCodePitchFormat)
        if self._output_format == ColorCodePitchFormat(0):
            # color code feature is disabled completely. skip.
            self._coloring_enabled = False
            return
        elif should_skip_coloring(self._token):
            # don't color special symbols and words without known pitch.
            self._coloring_enabled = False
            return
        elif self._cfg.pitch_accent.is_blocklisted(self._token.headword):
            self._coloring_enabled = False
            return
        else:
            self._coloring_enabled = True
            return

    def getvalue(self) -> str:
        if self._coloring_enabled:
            self._end_wrap()
        return super().getvalue()

    def _get_main_pitch_color(self, token: AccDbParsedToken) -> Optional[str]:
        """
        Determine pitch color based on available accents.
        If the word has many different accents (e.g. heiban and atamadaka),
        don't output anything because that might mislead the user.
        """
        main_pitch_type = guess_main_pitch_type(token)

        if main_pitch_type == PitchUnknown.none:
            # no accent => don't color-code.
            return None
        elif main_pitch_type == PitchUnknown.many:
            # by default many accents are marked grey.
            return self._cfg.pitch_color_codes.unknown
        elif self._cfg.furigana.color_code_kifuku:
            # non-heiban verbs and i-adjectives are commonly referred to as kifuku.
            main_pitch_type = adjust_if_kifuku(token.part_of_speech, main_pitch_type)
        try:
            return self._cfg.pitch_color_codes.lookup_color(main_pitch_type)
        except KeyError:
            return self._cfg.pitch_color_codes.unknown

    def _start_wrap(self) -> None:
        assert self._output_format != ColorCodePitchFormat(0)
        self.write(f'<span class="ajt__word_info"')
        pitch = self._token.describe_pitches(
            self._cfg.furigana.maximum_pitch_accents,
            self._cfg.furigana.hiragana_in_popups,
        )
        if ColorCodePitchFormat.attributes in self._output_format:
            self.write(f' part_of_speech="{self._token.part_of_speech.name}"')
            self.write(f' pitch="{pitch}"')
            self.write(f' headword="{self._token.headword}"')
        if html_color := self._get_main_pitch_color(self._token):
            self._write_inline_color(html_color)
        self.write(">")

    def _end_wrap(self) -> None:
        assert self._output_format != ColorCodePitchFormat(0)
        self.write("</span>")

    def _write_inline_color(self, html_color: str) -> None:
        """
        add inline styles for people who don't configure their css templates
        """
        assert self._output_format != ColorCodePitchFormat(0)
        # apply inline styles only when the pitch accent is not ambiguous
        if self._output_format & ~ColorCodePitchFormat.attributes == ColorCodePitchFormat(0):
            return
        self.write(f' style="')
        if ColorCodePitchFormat.color in self._output_format:
            self.write(f"color: {html_color};")
        if ColorCodePitchFormat.color | ColorCodePitchFormat.underline in self._output_format:
            # if color and underline are both enabled, add a space between the attributes.
            self.write(" ")
        if ColorCodePitchFormat.underline in self._output_format:
            self.write(
                f"text-decoration: underline; text-decoration-color: {html_color};"
                " text-decoration-thickness: 2px; text-underline-offset: 3px;"
            )
        self.write('"')
