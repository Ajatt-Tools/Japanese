# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import functools
import io
import pathlib
import re
from gettext import gettext as _
from types import SimpleNamespace
from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.utils import disable_help_button, openLink, show_critical, showInfo, tooltip
from aqt.webview import AnkiWebView

from ..ajt_common.about_menu import menu_root_entry
from ..ajt_common.enum_select_combo import EnumSelectCombo
from ..ajt_common.utils import ui_translate
from ..config_view import JapaneseConfig, SvgGraphReadingFormat, get_global_config
from ..helpers.consts import ADDON_NAME
from ..helpers.misc import media_strip
from ..helpers.regex import RE_SPACES
from ..helpers.webview_utils import (
    AJT_WEBVIEW_CSS_FILE_NAME,
    graphs_inline_css_style_tag,
)
from ..pitch_accents.colors import SvgGraphColorMode
from ..widgets.addon_opts import (
    AJTPlainTextEdit,
    AllowedRange,
    AllowedRangeDouble,
    PxDoubleNarrowSpinBox,
    PxNarrowSpinBox,
)
from ..widgets.raise_on_show_dialog import RaiseOnShowDialog
from ..widgets.webview import SVGPreviewWebView, get_svg_preview_webview
from ..widgets.widgets_to_config_dict import (
    as_config_dict,
    change_event,
    get_from_widget,
    set_from_cfg,
)
from .pitch_graph import SvgPitchArtistGraphMaker

ACTION_NAME = "Pitch artist"
USER_GUIDE_URL = "https://ajatt.top/blog/pitch-artist-user-guide.html"
EXAMPLES = """
dひとり;2 で dくすり;0 を のんだ;1
わたし; は;p にほんご; を べんきょう; して; います;k2
ぼく;1 は;p せんせい;3 を して;0 います;k2
くるま;0 が すき;2 です か
わたし;0 は だいがく;0 の せんせい;3 です
きょう;1 は;p | てんき;1 が いい;1 です
でんわ;0 を かける;k2
""".strip()


class GraphCodeEdit(AJTPlainTextEdit):
    """A text editor that triggers graph updates on Ctrl+Enter."""

    settings_changed = pyqtSignal()
    _font_size: int = 16

    def __init__(self) -> None:
        """Initialize the Pitch Artist notation editor."""
        super().__init__()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Ctrl+Enter to trigger graph update."""
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.settings_changed.emit()
        super().keyPressEvent(event)


class FormWidgets(SimpleNamespace):
    """Container for Pitch Artist settings form widgets."""

    circle_radius: PxDoubleNarrowSpinBox
    stroke_width: PxDoubleNarrowSpinBox
    graph_height: PxNarrowSpinBox
    graph_font_name: QLineEdit
    reading_format: EnumSelectCombo
    color_mode: EnumSelectCombo
    include_text: QCheckBox


class GraphSettingsWidget(QWidget):
    """A settings panel with controls for graph rendering parameters."""

    settings_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None, cfg: JapaneseConfig) -> None:
        """Initialize the settings panel for the provided add-on configuration."""
        super().__init__(parent)
        self._cfg = cfg
        self._form_layout = QFormLayout(self)

        # Create widgets.
        self._widgets = FormWidgets()
        self._widgets.circle_radius = PxDoubleNarrowSpinBox(allowed_range=AllowedRangeDouble(0, 999))
        self._widgets.stroke_width = PxDoubleNarrowSpinBox(allowed_range=AllowedRangeDouble(0, 999))
        self._widgets.graph_height = PxNarrowSpinBox(allowed_range=AllowedRange(0, 999))
        self._widgets.graph_font_name = QLineEdit()
        self._widgets.reading_format = EnumSelectCombo(enum_type=SvgGraphReadingFormat)
        self._widgets.color_mode = EnumSelectCombo(enum_type=SvgGraphColorMode)
        self._widgets.include_text = QCheckBox("Include text")

        self.setLayout(self._form_layout)
        self._set_initial_values()
        self._fill_layout()

    @property
    def color_mode(self) -> SvgGraphColorMode:
        """Return the selected SVG graph color mode."""
        return SvgGraphColorMode[get_from_widget(self._widgets.color_mode)]

    def _fill_layout(self) -> None:
        """Populate the form layout with config widgets and connect change signals."""
        for cfg_key, widget in self._widgets.__dict__.items():
            if isinstance(widget, QCheckBox):
                self._form_layout.addRow(widget)
            else:
                self._form_layout.addRow(ui_translate(cfg_key), widget)
            qconnect(change_event(widget), lambda: self.settings_changed.emit())

    def as_dict(self) -> dict[str, Any]:
        """Return a dict of all current config key-value pairs from the widgets."""
        return as_config_dict(self._widgets.__dict__)

    def _set_initial_values(self) -> None:
        """Load graph settings from the configuration into the form widgets."""
        set_from_cfg(self._widgets.circle_radius, self._cfg.svg_graphs.circle_radius)
        set_from_cfg(self._widgets.stroke_width, self._cfg.svg_graphs.stroke_width)
        set_from_cfg(self._widgets.graph_height, self._cfg.svg_graphs.graph_height)
        set_from_cfg(self._widgets.graph_font_name, self._cfg.svg_graphs.graph_font_name)
        set_from_cfg(self._widgets.reading_format, self._cfg.svg_graphs.reading_format)
        set_from_cfg(self._widgets.color_mode, self._cfg.svg_graphs.color_mode)
        set_from_cfg(self._widgets.include_text, self._cfg.svg_graphs.include_text)


def inline_css_code(code: str) -> str:
    """Collapse multi-line code into a single line with normalized whitespace."""
    return re.sub(RE_SPACES, " ", code.replace("\n", " ").strip())


def format_graph_as_html(graph: str, index: int) -> str:
    """Format a single SVG graph string as HTML with a save button."""
    html = io.StringIO()
    html.write('<div class="svg_wrap">')
    html.write(f'<div class="svg_graph">{graph}</div>')
    html.write(f'<button type="button" name="button" onclick="pycmd(\'ajt__save_graph:{index}\');">Save</button>')
    html.write("</div>")
    return html.getvalue()


def make_graphs_list(text: str, gen: SvgPitchArtistGraphMaker) -> list[str]:
    """Parse text into pitch accent sequences and return a list of SVG graphs."""
    if text := media_strip(text.replace("\n", "<br>")).strip():
        seq_sequences = gen.make_sequences(text)
        graphs = list(gen.make_graphs(seq_sequences))
        return graphs
    return []


def inject_css_into_svg(graph: str) -> str:
    """Inline pitch graph CSS into a standalone SVG string."""
    return graph.replace("</svg>", inline_css_code(graphs_inline_css_style_tag()) + "</svg>")


class PitchArtistDialog(RaiseOnShowDialog):
    """A dialog for previewing, editing, and saving pitch accent graphs."""

    name: str = "ajt__pitch_artist_dialog"

    _graphs_list: list[str]
    _webview: SVGPreviewWebView

    def __init__(self, cfg: JapaneseConfig, *, parent: QWidget | None = None) -> None:
        """Initialize the Pitch Artist preview dialog."""
        super().__init__(parent)
        disable_help_button(self)
        self._cfg = cfg
        self._graphs_list = []
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        self._graph_settings_dialog = GraphSettingsWidget(self, self._cfg)
        self._text_edit = GraphCodeEdit()
        self._webview = get_svg_preview_webview(
            self,
            action_name=ACTION_NAME,
            css_file_names=(AJT_WEBVIEW_CSS_FILE_NAME,),
        )
        self._webview.set_bridge_command(self.handle_save_button, self)
        self._setup_ui()
        self._set_initial_values()
        # pass update fn
        qconnect(self._text_edit.settings_changed, lambda: self.update_graphs())
        qconnect(self._graph_settings_dialog.settings_changed, lambda: self.update_graphs())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Ctrl+Plus/Minus for zooming the web view."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self._webview.zoom_in()
            elif event.key() == Qt.Key.Key_Minus:
                self._webview.zoom_out()
        super().keyPressEvent(event)

    def _setup_ui(self) -> None:
        """Initialize the dialog layout with splitter, web view, and buttons."""
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowTitle(f"{ADDON_NAME} - {ACTION_NAME}")
        self._splitter.addWidget(self.make_top_widget())
        self._splitter.addWidget(self._webview)
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self._splitter)
        layout.addLayout(self._make_bottom_buttons())
        self.setLayout(layout)

    def make_top_widget(self) -> QSplitter:
        """Create the top splitter containing the text editor and settings panel."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._text_edit)
        splitter.addWidget(self._graph_settings_dialog)
        splitter.setSizes([300, 100])
        return splitter

    def _set_initial_values(self) -> None:
        """Configure initial sizes, policies, and content for the dialog widgets."""
        self.setMinimumSize(400, 300)

        self._webview.setAcceptDrops(False)
        self._webview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._webview.setMinimumHeight(300)

        self._text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._text_edit.setMaximumHeight(400)
        self._text_edit.setMinimumHeight(50)
        self._text_edit.adjustSize()
        self._text_edit.setPlainText(self._cfg.pitch_artist.last_inserted_text)

        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 3)

    def set_text(self, text: str) -> "PitchArtistDialog":
        """Set the text editor content and return self for method chaining."""
        self._text_edit.setPlainText(text)
        return self

    def _format_graphs_as_html(self, graphs: list[str] | None) -> str:
        """Create the preview page body for generated SVG graphs."""
        html = io.StringIO()
        html.write('<main class="ajt__pitch_graphs">')
        if graphs:
            sep = self._cfg.pitch_artist.separator_expression_graphs
            graphs_html = sep.join(format_graph_as_html(graph, index) for index, graph in enumerate(graphs))
        else:
            graphs_html = "There's nothing to show."
        html.write(graphs_html)
        html.write("</main>")
        return html.getvalue()

    def update_graphs(self, _checked: bool = False) -> None:
        """Regenerate and display pitch graphs using the current settings and text."""
        cfg = self._cfg.clone()
        cfg.svg_graphs.update(self._graph_settings_dialog.as_dict())
        gen = SvgPitchArtistGraphMaker(cfg)
        text = self._text_edit.toPlainText()
        self._graphs_list = make_graphs_list(text, gen)
        self._webview.set_formatted_html(
            self._format_graphs_as_html(self._graphs_list),
            color_mode=cfg.svg_graphs.color_mode,
        )

    def handle_save_button(self, bridge_cmd: str) -> None:
        """Handle the save button bridge command to export a graph as an SVG file."""
        if not bridge_cmd.startswith("ajt__save_graph:"):
            return
        try:
            index = int(bridge_cmd.split(":", maxsplit=1)[-1])
            graph = self._graphs_list[index]
        except (ValueError, IndexError, TypeError):
            return
        name, mime = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save pitch graph as SVG File",
            directory=str(self._cfg.pitch_artist.last_save_location),
        )
        if not name:
            tooltip("Aborted.")
            return
        graph = inject_css_into_svg(graph) if self._graph_settings_dialog.color_mode == SvgGraphColorMode.css else graph
        try:
            with open(name, "w", encoding="utf8") as of:
                of.write(graph)
        except OSError as ex:
            show_critical(f"Failed to save file to '{name}': {ex}", parent=self)
        else:
            self._cfg.pitch_artist.last_save_location = pathlib.Path(name).resolve()
            self._cfg.write_config()

    def copy_graphs_as_simple_str(self) -> None:
        """Copy all generated SVG graphs to the system clipboard as a joined string."""
        if not self._graphs_list:
            return
        sep = self._cfg.pitch_artist.separator_expression_graphs
        graphs = (
            [inject_css_into_svg(graph) for graph in self._graphs_list]
            if self._graph_settings_dialog.color_mode == SvgGraphColorMode.css
            else self._graphs_list
        )
        if clip := QApplication.clipboard():
            clip.setText(sep.join(graphs))

    def show(self) -> None:
        """Show the dialog, restore saved geometry, and render initial graphs."""
        super().show()
        self.update_graphs()

    def done(self, result: int) -> None:
        """Save geometry and last-inserted text before closing the dialog."""
        self._cfg.pitch_artist.last_inserted_text = self._text_edit.toPlainText()
        self._cfg.write_config()
        super().done(result)

    def _make_bottom_buttons(self) -> QLayout:
        """Create the bottom button row with Update, Ok, and Copy buttons."""
        buttons = (
            # lambda throws away passed args
            ("Update", lambda checked: self.update_graphs(), "Ctrl+Enter to update"),
            ("Ok", lambda checked: self.accept(), "Accept and close the dialog"),
            (
                "Copy SVG to Clipboard",
                lambda checked: self.copy_graphs_as_simple_str(),
                "Copy the graphs to the system clipboard",
            ),
            ("Examples", lambda checked: self._present_examples(), "Show examples"),
        )
        hbox = QHBoxLayout()
        for label, action, tooltip_text in buttons:
            button = QPushButton(label)
            button.setToolTip(tooltip_text)
            qconnect(button.clicked, action)
            hbox.addWidget(button)
        hbox.addStretch(1)
        hbox.addWidget(self._make_user_guide_button())
        return hbox

    def _make_user_guide_button(self) -> QPushButton:
        """Create a button that opens the official Pitch Artist user guide."""
        button = QPushButton("User Guide")
        button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        button.setToolTip("Open the official Pitch Artist user guide")
        qconnect(button.clicked, lambda checked: openLink(USER_GUIDE_URL))
        return button

    def _on_lookup_pronunciation(self, text: str) -> None:
        """Open the pitch graph preview dialog with the selected text."""
        if text := text.strip():
            self.set_text(text).show()
        else:
            showInfo(_("Empty selection."))

    def add_context_menu_item(self, webview: AnkiWebView, menu: QMenu) -> None:
        """Add a 'Preview pitch graphs' entry to the editor context menu."""
        menu.addAction(ACTION_NAME, functools.partial(self._on_lookup_pronunciation, webview.selectedText()))

    def _present_examples(self) -> None:
        """Prepend sample Pitch Artist notation and update the preview."""
        self.set_text(EXAMPLES + "\n" + self._text_edit.toPlainText())
        self.update_graphs()


def add_settings_action(root_menu: QMenu, dialog: PitchArtistDialog) -> None:
    """Add a menu action to open the Pitch Graph Artist dialog."""
    menu_action = QAction("🎨 Pitch &Graph Artist...", root_menu)
    qconnect(menu_action.triggered, lambda: dialog.show())
    root_menu.addAction(menu_action)


def init() -> None:
    """Initialize the Pitch Graph Artist dialog, menu entries, and context menu hooks."""
    assert mw, "Anki should be running."
    # Get config
    cfg = get_global_config()
    # init dialog
    mw._ajt__pitch_artist_dialog = dialog = PitchArtistDialog(cfg, parent=mw)
    # get AJT menu
    root_menu = menu_root_entry()
    # create a new menu item
    add_settings_action(root_menu, dialog)
    # Hook to context menu events
    gui_hooks.editor_will_show_context_menu.append(dialog.add_context_menu_item)
