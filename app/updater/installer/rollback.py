from __future__ import annotations

import logging
from pathlib import Path

from app.updater.exceptions import UpdatePackageValidationError, UpdateRollbackError
from app.updater.installer.filesystem import copy_path, iter_application_managed_paths, remove_path
from app.updater.models import BackupInfo

class RollbackManager:
    """Interface for restoring the previous application version."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("ScenarioRPUpdater")

    def rollback(self, app_dir: Path, backup_info: BackupInfo) -> None:
        """Restore the application from the latest backup."""
        try:
            self.logger.info("Rollback removing newly installed application-managed files")
            for path in iter_application_managed_paths(app_dir):
                remove_path(path, app_dir)
            self.logger.info("Rollback restoring backup from %s", backup_info.backup_dir)
            for relative in backup_info.backed_up_paths:
                source = backup_info.backup_dir / Path(relative)
                destination = app_dir / Path(relative)
                copy_path(source, destination, app_dir)
            executable = app_dir / "ScenarioRP-Manager.exe"
            if not executable.is_file():
                raise UpdatePackageValidationError("Rollback did not restore ScenarioRP-Manager.exe.")
            self.logger.info("Rollback completed successfully")
        except Exception as exc:
            if isinstance(exc, UpdateRollbackError):
                raise
            raise UpdateRollbackError(f"Rollback failed using backup {backup_info.backup_dir}") from exc
