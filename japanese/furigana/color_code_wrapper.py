# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
import io
from typing import Optional

from ..helpers.profiles import ColorCodePitchFormat
from ..mecab_controller.basic_types import PartOfSpeech
from ..pitch_accents.basic_types import AccDbParsedToken, PitchType, PitchColor

SKIP_COLORING = (
    PartOfSpeech.other,
    PartOfSpeech.filler,
    PartOfSpeech.particle,
    PartOfSpeech.symbol,
)


def should_skip_coloring(token: AccDbParsedToken) -> bool:
    """
    Don't color special symbols and words without known pitch.
    """
    return token.part_of_speech in SKIP_COLORING or not token.headword_accents


def get_main_pitch_color(token: AccDbParsedToken) -> Optional[str]:
    """
    Determine pitch color based on available accents.
    If the word has many different accents (e.g. heiban and atamadaka),
    don't output anything because that might mislead the user.
    """
    main_pitch_type: Optional[PitchType] = None
    for entry in token.headword_accents:
        for accent in entry.pitches:
            if not main_pitch_type:
                main_pitch_type = accent.type
            elif main_pitch_type != accent.type:
                return PitchColor.unknown.value
    if not main_pitch_type:
        return None
    try:
        return PitchColor[main_pitch_type.name].value
    except KeyError:
        return PitchColor.unknown.value


class ColorCodeWrapper(io.StringIO):
    _token: AccDbParsedToken
    _output_format: ColorCodePitchFormat
    _coloring_enabled: bool = True

    def __init__(self, token: AccDbParsedToken, output_format: ColorCodePitchFormat):
        super().__init__()
        self._token = token
        self._output_format = output_format
        self._set_coloring()
        if self._coloring_enabled:
            self.start_wrap()

    def _set_coloring(self) -> None:
        if self._output_format == ColorCodePitchFormat.none:
            # color code feature is disabled completely. skip.
            self._coloring_enabled = False
        elif should_skip_coloring(self._token):
            # don't color special symbols and words without known pitch.
            self._coloring_enabled = False

    def getvalue(self) -> str:
        if self._coloring_enabled:
            self.end_wrap()
        return super().getvalue()

    def start_wrap(self) -> None:
        self.write(f'<span class="ajt__word_info"')
        self.write(f' part_of_speech="{self._token.part_of_speech.name}"')
        self.write(f' pitch="{self._token.describe_pitches()}"')
        self._write_inline_style()
        self.write(">")

    def end_wrap(self) -> None:
        self.write("</span>")

    def _write_inline_style(self) -> None:
        """
        add inline styles for people who don't configure their css templates
        """
        if html_color := get_main_pitch_color(self._token):
            if self._output_format == ColorCodePitchFormat.none:
                return
            elif self._output_format == ColorCodePitchFormat.color:
                self.write(f' style="color: {html_color}"')
            elif self._output_format == ColorCodePitchFormat.underline:
                self.write(
                    f' style="text-decoration: underline; text-decoration-color: {html_color};'
                    f' text-decoration-thickness: 2px; text-underline-offset: 3px;"'
                )
            else:
                raise ValueError(f"can't handle {self._output_format}")
