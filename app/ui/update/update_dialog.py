from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.updater.models import UpdateRelease


class UpdateDialog(QDialog):
    """Dialog that presents an available update and download progress."""

    download_requested = Signal(object)

    def __init__(self, current_version: str, release: UpdateRelease, parent: object | None = None) -> None:
        super().__init__(parent)
        self.current_version = current_version
        self.release = release
        self._download_in_progress = False

        self.setWindowTitle("נמצא עדכון חדש")
        self.setMinimumWidth(520)
        self._build_ui()

    @property
    def download_in_progress(self) -> bool:
        return self._download_in_progress

    def start_download(self) -> None:
        """Switch the dialog into download mode."""
        if self._download_in_progress:
            return
        self._download_in_progress = True
        self.download_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("מתחיל הורדה...")

    def set_download_progress(self, downloaded_bytes: int, total_bytes: int, percent: int) -> None:
        """Update the progress bar and progress text."""
        if total_bytes > 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"{self._format_bytes(downloaded_bytes)} מתוך {self._format_bytes(total_bytes)}")
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_label.setText(f"{self._format_bytes(downloaded_bytes)} הורדו")

    def show_download_finished(self, path: Path) -> None:
        """Show that the update file was downloaded successfully."""
        self._download_in_progress = False
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"הקובץ הורד בהצלחה: {path}")
        self.later_button.setText("סגור")
        self.later_button.setEnabled(True)
        QMessageBox.information(self, "ההורדה הסתיימה", f"קובץ העדכון הורד בהצלחה:\n{path}")

    def show_download_error(self, message: str) -> None:
        """Show a download error and allow retry."""
        self._download_in_progress = False
        self.download_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_label.setText("ההורדה נכשלה.")
        QMessageBox.warning(self, "שגיאת הורדה", message)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title_label = QLabel("נמצא עדכון חדש")
        title_label.setObjectName("dialogTitleLabel")
        layout.addWidget(title_label)

        layout.addWidget(QLabel(f"גרסה נוכחית: {self.current_version}"))
        layout.addWidget(QLabel(f"גרסה חדשה: {self.release.version}"))

        layout.addWidget(QLabel("הערות גרסה:"))
        self.release_notes = QPlainTextEdit(self.release.release_notes or "אין הערות גרסה.")
        self.release_notes.setReadOnly(True)
        self.release_notes.setMinimumHeight(140)
        layout.addWidget(self.release_notes)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        buttons = QDialogButtonBox()
        self.download_button = QPushButton("הורד עדכון")
        self.later_button = QPushButton("אחר כך")
        buttons.addButton(self.download_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self.later_button, QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(buttons)

        self.download_button.clicked.connect(self._request_download)
        self.later_button.clicked.connect(self.reject)

    def _request_download(self) -> None:
        if self._download_in_progress:
            return
        self.start_download()
        self.download_requested.emit(self.release)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._download_in_progress:
            self.progress_label.setText("ההורדה עדיין פעילה. המתן לסיום ההורדה.")
            event.ignore()
            return
        super().closeEvent(event)

    def _format_bytes(self, value: int) -> str:
        size = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"
