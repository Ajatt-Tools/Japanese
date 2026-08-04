# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from .settings_form import AllowedConfigValues, SettingsForm


class NoAnkiWebView(QWebEngineView):
    """Standalone web view that mimics AnkiWebView.stdHtml for tests and playground scripts."""

    def stdHtml(self, body: str, head: str) -> None:
        """Set a complete HTML page from head and body fragments."""
        return self.setHtml(f"""
        <html>
        <head>{head}</head>
        <body>{body}</body>
        </html>
        """)


class GroupBoxWrapper(QGroupBox):
    """Wrap a settings form in a titled group box while preserving its config export API."""

    def __init__(self, settings_form: SettingsForm, *args) -> None:
        """Initialize the wrapper from a settings form."""
        super().__init__(*args)
        self._form = settings_form
        self.setTitle(settings_form.title)
        self.setCheckable(False)
        self.setLayout(settings_form.layout())

    def as_dict(self) -> dict[str, AllowedConfigValues]:
        """Return the wrapped settings form values as a config dictionary."""
        return self._form.as_dict()
