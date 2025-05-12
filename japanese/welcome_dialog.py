# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
from anki.models import NotetypeNameId
from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.utils import openLink
from aqt.webview import AnkiWebView

from .ajt_common.about_menu import tweak_window
from .ajt_common.consts import (
    ADDON_SERIES,
    COMMUNITY_LINK,
    DONATE_LINK,
    GITHUB_LINK,
    TG_LINK,
)
from .ajt_common.model_utils import get_model_field_names
from .ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog
from .config_view import config_view as cfg
from .gui import EXAMPLE_DECK_ANKIWEB_URL
from .helpers.consts import ADDON_NAME
from .helpers.webview_utils import anki_addon_web_relpath

GUIDE_LINK = "https://tatsumoto.neocities.org/blog/table-of-contents.html"
RESOURCES_LINK = "https://tatsumoto.neocities.org/blog/resources.html"
FAQ_LINK = "https://tatsumoto.neocities.org/blog/tag_faq.html"
AJATT_LINK = "https://tatsumoto.neocities.org/blog/whats-ajatt.html"
ADDON_MANUAL = "https://tatsumoto.neocities.org/blog/anki-japanese-support.html"
ACTION_NAME = f"Welcome to {ADDON_NAME}!"
NOTE_TYPE_NAME = "Japanese sentences"
REQUIRED_FIELDS = {
    "SentKanji",
    "VocabKanji",
    "VocabDef",
    "SentAudio",
    "VocabAudio",
}
WELCOME_PAGE = f"""
<main class="ajt__welcome">
<article>
<h1>{ACTION_NAME}</h1>
<p>
Thank you for choosing {ADDON_NAME}!
At <a href="{AJATT_LINK}">AJATT</a>, we hope that you will enjoy using {ADDON_NAME}
as much as we enjoy building it.
Before you start learning Japanese,
we strongly recommend that you read the <a href="{GUIDE_LINK}">AJATT guide</a>.
To get familiar with the add-on, read the <a href="{ADDON_MANUAL}">{ADDON_NAME} manual</a>. 
To open the the Settings dialog, select <code>{ADDON_SERIES}</code> &gt; <code>Japanese options</code>.
</p>
<p>
After you install Anki, you need to set up a Note Type for learning Japanese.
Anki comes with a few basic Note Types, but they aren't suited for Japanese.
To ensure that {ADDON_NAME} works out of the box without additional configuration,
it is recommended to use AJATT's pre-configured Note Type.
The Note Type is bundled with the <a href="{EXAMPLE_DECK_ANKIWEB_URL}">example Anki deck</a>.
To configure Note Types, select <code>Tools</code> &gt; <code>Manage Note Types</code>. 
</p>
</article>
</main>
"""


def note_type_looks_right(model: NotetypeNameId) -> bool:
    assert mw
    return frozenset(get_model_field_names(mw.col.models.get(model.id))) & REQUIRED_FIELDS == REQUIRED_FIELDS


def is_note_type_installed() -> bool:
    assert mw
    for model in mw.col.models.all_names_and_ids():
        if model.name == NOTE_TYPE_NAME and note_type_looks_right(model):
            return True
    return False


class NoteTypeNagBar(QGroupBox):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Japanese note type")
        self.setCheckable(False)
        if is_note_type_installed():
            self.setHidden(True)
        else:
            self._setup_ui()

    def _setup_ui(self):
        self.setLayout(layout := QHBoxLayout())
        layout.addWidget(label := QLabel("Note Type is not installed!"))
        label.setStyleSheet("QLabel { color: brown; font-weight: bold; }")
        layout.addWidget(dl_b := QPushButton("Download"))
        qconnect(dl_b.clicked, lambda: openLink(EXAMPLE_DECK_ANKIWEB_URL))
        dl_b.setStyleSheet("QPushButton { background-color: rgba(0, 255, 0, 30); }")


class LearnJapaneseButtons(QGroupBox):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Learn Japanese")
        self.setCheckable(False)
        self._setup_ui()

    def _setup_ui(self):
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(b := QPushButton("Japanese guide"))
        qconnect(b.clicked, lambda: openLink(GUIDE_LINK))
        layout.addWidget(b := QPushButton("Resources"))
        qconnect(b.clicked, lambda: openLink(RESOURCES_LINK))
        layout.addWidget(b := QPushButton("FAQ"))
        qconnect(b.clicked, lambda: openLink(FAQ_LINK))


class CommunityButtons(QGroupBox):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Community")
        self.setCheckable(False)
        self._setup_ui()

    def _setup_ui(self):
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(b := QPushButton("Join chat"))
        qconnect(b.clicked, lambda: openLink(COMMUNITY_LINK))
        layout.addWidget(b := QPushButton("Subscribe on Telegram"))
        qconnect(b.clicked, lambda: openLink(TG_LINK))


class ProjectButtons(QGroupBox):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Project")
        self.setCheckable(False)
        self._setup_ui()

    def _setup_ui(self):
        self.setLayout(layout := QVBoxLayout())
        layout.addWidget(b := QPushButton("Gen involved"))
        qconnect(b.clicked, lambda: openLink(GITHUB_LINK))
        layout.addWidget(b := QPushButton("Keep the project alive"))
        qconnect(b.clicked, lambda: openLink(DONATE_LINK))


class AJTWelcomeDialog(AnkiSaveAndRestoreGeomDialog):
    name: str = "ajt__welcome_screen"
    _css_relpath: str = f"{anki_addon_web_relpath()}/ajt_webview.css"
    _web: AnkiWebView

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._web = AnkiWebView(parent=self, title=ACTION_NAME)
        self._web.setProperty("url", QUrl("about:blank"))
        self._web.setObjectName(self.name)
        self._web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._note_type_nagbar = NoteTypeNagBar()
        self._learn_buttons = LearnJapaneseButtons()
        self._community_buttons = CommunityButtons()
        self._project_buttons = ProjectButtons()
        self._show_at_start_checkbox = QCheckBox("Show this dialog when Anki starts")
        self._show_at_start_checkbox.setChecked(cfg.show_welcome_guide)
        self._button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._setup_ui()
        self._connect_widgets()
        tweak_window(self)
        self.setFocus()

    def _setup_ui(self):
        self.setWindowTitle(ACTION_NAME)
        self.setMinimumSize(800, 600)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setLayout(layout := QGridLayout())
        self._web.stdHtml(WELCOME_PAGE, js=[], css=[self._css_relpath], context=self)
        # row: int, column: int, rowSpan: int, columnSpan: int
        layout.addWidget(self._web, 0, 0, 1, 3)
        layout.addWidget(self._note_type_nagbar, 1, 0, 1, 3)
        layout.addWidget(self._learn_buttons, 2, 0, 1, 1)
        layout.addWidget(self._community_buttons, 2, 1, 1, 1)
        layout.addWidget(self._project_buttons, 2, 2, 1, 1)
        layout.addLayout(self._make_bottom_layout(), 3, 0, 1, 3)

    def _make_bottom_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self._show_at_start_checkbox)
        layout.addStretch(1)
        layout.addWidget(self._button_box)
        return layout

    def _connect_widgets(self) -> None:
        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)

    def done(self, result: int) -> None:
        # https://doc.qt.io/qt-6/qdialog.html#done
        self.on_close()
        return super().done(result)

    def on_close(self) -> None:
        print("closing AJT welcome window...")
        cfg.show_welcome_guide = self._show_at_start_checkbox.isChecked()
        cfg.write_config()


def show_welcome_dialog() -> None:
    """
    If the user hasn't installed the recommended note type,
    the add-on should ask them to install it to ensure that the add-on works out of the box.
    """
    assert mw

    if not cfg.show_welcome_guide or is_note_type_installed():
        return

    mw.progress.single_shot(1000, lambda: AJTWelcomeDialog(mw).show(), requires_collection=False)


def setup_welcome_action() -> None:
    """
    Press the shortcut to show the welcome page.
    """
    assert mw
    action = QAction(ACTION_NAME, mw)
    qconnect(action.triggered, lambda: AJTWelcomeDialog(mw).show())
    action.setShortcut(QKeySequence("Ctrl+Shift+w"))
    mw.addAction(action)


def init() -> None:
    gui_hooks.main_window_did_init.append(setup_welcome_action)
    gui_hooks.profile_did_open.append(show_welcome_dialog)
