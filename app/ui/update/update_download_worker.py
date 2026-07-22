from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.updater.client import UpdateManager
from app.updater.models import UpdateRelease


class UpdateDownloadWorker(QObject):
    """Downloads an update away from the UI thread."""

    progress = Signal(int, int, int)
    completed = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, manager: UpdateManager, release: UpdateRelease, destination_directory: Path) -> None:
        super().__init__()
        self.manager = manager
        self.release = release
        self.destination_directory = destination_directory

    @Slot()
    def run(self) -> None:
        """Download the update and report progress through signals."""
        try:
            path = self.manager.download_update(self.release, self.destination_directory, self._report_progress)
            self.completed.emit(path)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()

    def _report_progress(self, downloaded_bytes: int, total_bytes: int) -> None:
        percent = 0
        if total_bytes > 0:
            percent = max(0, min(100, int(downloaded_bytes * 100 / total_bytes)))
        self.progress.emit(downloaded_bytes, total_bytes, percent)
