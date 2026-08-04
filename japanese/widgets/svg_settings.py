# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from collections.abc import Iterable
from typing import TypeAlias

from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView

from ..ajt_common.color_picker import ColorEditPicker
from ..ajt_common.utils import q_emit
from ..config_view import JapaneseConfig, SvgGraphColorCodesConfigView
from ..helpers.webview_utils import (
    ajt_svg_settings_css,
    head_content,
    svg_settings_inline_css_style_tag,
)
from ..pitch_accents.colors import SvgGraphClassName, SvgGraphColorMode
from ..pitch_accents.common import FormattedEntry
from ..pitch_accents.entry_to_svg import FormattedEntryToSvgAdapter
from ..pitch_artist.pitch_accents_web_view import (
    get_css_file_refs,
    get_css_inline_styles,
)
from .common import NoAnkiWebView
from .settings_form import (
    AllowedConfigValues,
    MultiColumnSettingsForm,
    SvgSettingsForm,
)
from .widgets_to_config_dict import change_event

SHOW_ENTRIES = (
    FormattedEntry(
        "音楽家",
        "オンガクカ",
        "<low_rise>オ</low_rise><high>ンカ<nasal>&#176;</nasal><devoiced>ク</devoiced>カ</high>",
        "0",
    ),
    FormattedEntry(
        "数か月",
        "スウカゲツ",
        "<low_rise>ス</low_rise><high_drop>ウカ</high_drop><low>ゲツ</low>",
        "3",
    ),
    FormattedEntry(
        "淑女",
        "シュクジョ",
        "<high_drop><devoiced>シ</devoiced>ュ</high_drop><low>クジョ</low>",
        "1",
    ),
    FormattedEntry(
        "弟",
        "オトート",
        "<low_rise>オ</low_rise><high_drop>トート</high_drop>",
        "4",
    ),
)
DEBOUNCE_UPDATE_VIEW_MS = 200
SVG_SETTINGS_BODY_VERTICAL_PADDING = 8  # padding=3 + border=1


class SvgPitchColorCodesSettingsForm(MultiColumnSettingsForm):
    """Mirrors logic of PitchColorCodesSettingsForm for SVG graphs."""

    _columns: int = 3
    _title: str = "SVG Pitch Colors"
    _config: SvgGraphColorCodesConfigView

    opts_changed = pyqtSignal()

    def _make_color_line_edits(self) -> Iterable[tuple[str, ColorEditPicker]]:
        """Yield color picker widgets for every SVG graph class."""
        assert self._config, "config must be set"
        for pitch_type in SvgGraphClassName:
            picker = ColorEditPicker()
            picker.set_color(self._config.lookup_color(pitch_type))
            yield pitch_type.name, picker

    def _add_widgets(self) -> None:
        """Create color picker widgets and connect change signals."""
        super()._add_widgets()
        self._widgets.__dict__.update(self._make_color_line_edits())
        self._connect_widgets()

    def _connect_widgets(self) -> None:
        """Forward color picker changes through opts_changed."""
        for widget in self._widgets.__dict__.values():
            qconnect(change_event(widget), lambda: q_emit(self.opts_changed))


def get_svg_settings_css_file_refs(color_mode: SvgGraphColorMode) -> list[str]:
    """Return CSS files needed for the selected color mode."""
    return get_css_file_refs(color_mode=color_mode, includes=(ajt_svg_settings_css(),))


def get_svg_settings_inline_styles(color_mode: SvgGraphColorMode) -> Sequence[str]:
    """Return inline pitch graph CSS only when CSS color mode is active."""
    return get_css_inline_styles(color_mode=color_mode, includes=(svg_settings_inline_css_style_tag(),))


class AnkiSVGPreviewWebView(AnkiWebView):
    """An Anki web view used to preview SVG graph settings."""

    def __init__(self, parent: QWidget | None) -> None:
        """Initialize the preview web view with a stable title."""
        super().__init__(parent=parent, title="Preview SVG graphs")

    def set_svg_preview(self, formatted_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set the preview page using Anki's web-exported CSS files."""
        self.stdHtml(
            head=head_content(),
            css=get_svg_settings_css_file_refs(color_mode),
            body=formatted_html,
        )


class NoAnkiSVGPreviewWebView(NoAnkiWebView):
    """A standalone SVG settings preview web view for tests and playground scripts."""

    def set_svg_preview(self, formatted_html: str, color_mode: SvgGraphColorMode) -> None:
        """Set the preview page with CSS inlined from local files."""
        self.stdHtml(
            head=head_content() + "".join(get_svg_settings_inline_styles(color_mode)),
            body=formatted_html,
        )


SVGPreviewWebView: TypeAlias = AnkiSVGPreviewWebView | NoAnkiSVGPreviewWebView


def get_preview_webview(parent: QWidget) -> SVGPreviewWebView:
    """Return the Anki or standalone web view for the lookup dialog."""
    if mw:
        return AnkiSVGPreviewWebView(parent)
    return NoAnkiSVGPreviewWebView(parent)


class SvgSettingsWidget(QWidget):
    """Widget that edits SVG graph settings and renders a live preview."""

    _web_view: SVGPreviewWebView
    _update_view_timer: QTimer

    def __init__(self, cfg: JapaneseConfig, svg_maker: FormattedEntryToSvgAdapter | None = None) -> None:
        """Initialize settings forms, preview web view, and debounced updates."""
        super().__init__()
        self._cfg_clone = cfg.clone()
        self._form = SvgSettingsForm(self._cfg_clone.svg_graphs)
        self._web_view = get_preview_webview(self)
        self._svg_maker = svg_maker or FormattedEntryToSvgAdapter(self._cfg_clone)
        self._color_settings = SvgPitchColorCodesSettingsForm(cfg.svg_graph_colors)
        self._init_update_view_timer()
        self._init_ui()
        self.update_view()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect settings changes to debounced preview updates."""
        qconnect(self._form.opts_changed, self._schedule_update_view)
        qconnect(self._color_settings.opts_changed, self._schedule_update_view)

    def _init_update_view_timer(self) -> None:
        """Create the single-shot timer used to debounce preview updates."""
        self._update_view_timer = QTimer(self)
        self._update_view_timer.setSingleShot(True)
        self._update_view_timer.setInterval(DEBOUNCE_UPDATE_VIEW_MS)
        qconnect(self._update_view_timer.timeout, self.update_view)

    def _schedule_update_view(self) -> None:
        """Schedule a debounced preview update."""
        self._update_view_timer.start()

    def _init_ui(self) -> None:
        """Arrange the preview, graph settings, and color settings widgets."""
        layout = QVBoxLayout()
        # row: int, column: int, rowSpan: int, columnSpan: int
        layout.addWidget(self._web_view, stretch=1)
        layout.addWidget(self._form, stretch=0)
        layout.addWidget(self._color_settings, stretch=0)
        self._web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self._web_view.setMinimumHeight(self._preview_minimum_height())
        self.setLayout(layout)

    def update_view(self) -> None:
        """Apply form values to the preview config and redraw the SVG preview."""
        # Update the cloned config so preview graphs reflect unsaved settings without mutating the live config.
        self._cfg_clone.svg_graphs.update(self._form.as_dict())
        self._cfg_clone.svg_graph_colors.update(self._color_settings.as_dict())
        self._web_view.set_svg_preview(
            formatted_html=self._make_svgs(), color_mode=self._cfg_clone.svg_graphs.color_mode
        )
        self._web_view.setMinimumHeight(self._preview_minimum_height())

    def _preview_minimum_height(self) -> int:
        """Return the minimum height needed for the current preview graph size."""
        return self._cfg_clone.svg_graphs.graph_visible_height + SVG_SETTINGS_BODY_VERTICAL_PADDING

    def _make_svgs(self) -> str:
        """Render preview SVGs for the sample entries."""
        return "".join(self._svg_maker.make_graph(entry) for entry in SHOW_ENTRIES)

    def svg_colors_as_dict(self) -> dict[str, AllowedConfigValues]:
        """Return current SVG color settings as a config dictionary."""
        return self._color_settings.as_dict()

    def svg_settings_as_dict(self) -> dict[str, AllowedConfigValues]:
        """Return current SVG graph settings as a config dictionary."""
        return self._form.as_dict()
