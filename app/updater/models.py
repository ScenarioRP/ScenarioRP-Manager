from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class UpdateRelease:
    """Metadata for an available application update."""

    version: str
    download_url: str
    file_name: str
    release_notes: str | None
    checksum: str | None
    is_prerelease: bool


@dataclass(frozen=True)
class InstallerConfig:
    """Command-line configuration for the future standalone updater executable."""

    app_dir: Path
    zip_path: Path
    timeout_seconds: float = 120.0
    manager_pid: int | None = None

    @property
    def updates_dir(self) -> Path:
        return self.app_dir / "user_data" / "updates"

    @property
    def downloads_dir(self) -> Path:
        return self.updates_dir / "downloads"

    @property
    def extracted_dir(self) -> Path:
        return self.updates_dir / "extracted"

    @property
    def backups_dir(self) -> Path:
        return self.updates_dir / "backups"

    @property
    def log_path(self) -> Path:
        return self.updates_dir / "update.log"

    @property
    def manager_executable(self) -> Path:
        return self.app_dir / "ScenarioRP-Manager.exe"


@dataclass(frozen=True)
class BackupInfo:
    """Information about a backup created for one update transaction."""

    backup_dir: Path
    manifest_path: Path
    app_dir: Path
    created_at: datetime
    backed_up_paths: tuple[str, ...]


@dataclass(frozen=True)
class ReplacementState:
    """State tracked while replacing application files."""

    removed_paths: tuple[str, ...]
    copied_paths: tuple[str, ...]
