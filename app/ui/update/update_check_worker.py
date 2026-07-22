from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.updater.client import UpdateManager
from app.updater.models import UpdateRelease


class UpdateCheckWorker(QObject):
    """Runs an update check away from the UI thread."""

    update_available = Signal(object)
    no_update = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self, manager: UpdateManager) -> None:
        super().__init__()
        self.manager = manager

    @Slot()
    def run(self) -> None:
        """Check for an update and report the result through signals."""
        try:
            release: UpdateRelease | None = self.manager.check_for_update()
            if release is None:
                self.no_update.emit()
            else:
                self.update_available.emit(release)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
