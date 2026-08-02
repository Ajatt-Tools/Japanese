# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

from .settings_form import SettingsForm, AllowedConfigValues


class NoAnkiWebView(QWebEngineView):
    def stdHtml(self, body: str, head: str) -> None:
        return self.setHtml(f"""
        <html>
        <head>{head}</head>
        <body>{body}</body>
        </html>
        """)


class GroupBoxWrapper(QGroupBox):
    def __init__(self, settings_form: SettingsForm, *args) -> None:
        super().__init__(*args)
        self._form = settings_form
        self.setTitle(settings_form.title)
        self.setCheckable(False)
        self.setLayout(settings_form.layout())

    def as_dict(self) -> dict[str, AllowedConfigValues]:
        return self._form.as_dict()
