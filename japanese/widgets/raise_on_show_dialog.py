# Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from ..ajt_common.restore_geom_dialog import AnkiSaveAndRestoreGeomDialog


class RaiseOnShowDialog(AnkiSaveAndRestoreGeomDialog):
    """A persistent dialog that raises above other windows every time it is shown.

    Persistent dialogs are created once and reused, so they may already be open
    behind another window when triggered again. show() on an already-visible
    widget does not raise it, hence the explicit raise_().
    https://doc.qt.io/qt-6/qwidget.html#raise

    Note: tweak_window() must not be used with persistent dialogs. It registers
    the dialog for deleteLater() when it finishes, but persistent dialogs must
    survive closing. Call disable_help_button() instead.
    """

    def show(self) -> None:
        """Show the dialog and raise it above other windows."""
        if self.isVisible():
            # Already visible: just raise. Calling super().show() would re-run
            # _restore_geom() and snap the dialog back to its saved position,
            # discarding any move the user made while the dialog was open.
            self.raise_()
            return
        super().show()
        self.raise_()
