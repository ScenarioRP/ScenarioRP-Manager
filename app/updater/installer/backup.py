from __future__ import annotations

from pathlib import Path


class BackupManager:
    """Interface for backing up current application files."""

    def create_backup(self, app_dir: Path) -> Path:
        """Create a backup for app_dir and return the backup directory."""
        raise NotImplementedError("Backup creation is not implemented yet.")
