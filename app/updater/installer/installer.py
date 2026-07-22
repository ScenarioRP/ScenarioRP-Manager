from __future__ import annotations

import logging
from pathlib import Path

from app.updater.exceptions import UpdatePackageValidationError, UpdateReplacementError
from app.updater.installer.filesystem import copy_path, iter_application_managed_paths, remove_path
from app.updater.installer.backup import BackupManager
from app.updater.installer.extractor import UpdateExtractor
from app.updater.installer.launcher import ApplicationLauncher
from app.updater.installer.rollback import RollbackManager
from app.updater.installer.validator import UpdateValidator
from app.updater.models import BackupInfo, InstallerConfig, ReplacementState


class UpdateInstaller:
    """Installs a downloaded ScenarioRP Manager update package."""

    def __init__(
        self,
        config: InstallerConfig,
        logger: logging.Logger | None = None,
        validator: UpdateValidator | None = None,
        extractor: UpdateExtractor | None = None,
        backup_manager: BackupManager | None = None,
        rollback_manager: RollbackManager | None = None,
        launcher: ApplicationLauncher | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("ScenarioRPUpdater")
        self.validator = validator or UpdateValidator()
        self.extractor = extractor or UpdateExtractor()
        self.backup_manager = backup_manager or BackupManager()
        self.rollback_manager = rollback_manager or RollbackManager(self.logger)
        self.launcher = launcher or ApplicationLauncher(self.logger)
        self.extracted_package_dir: Path | None = None
        self.extraction_root: Path | None = None
        self.backup_info: BackupInfo | None = None
        self.replacement_started = False
        self.rollback_attempted = False
        self.replacement_state: ReplacementState | None = None

    def run(self) -> None:
        """Run the full install flow with rollback after backup."""
        self.logger.info("Updater start")
        self.logger.info("Parsed arguments: app=%s zip=%s timeout=%s pid=%s",
                         self.config.app_dir, self.config.zip_path, self.config.timeout_seconds, self.config.manager_pid)
        try:
            self.validate_arguments()
            self.wait_for_manager_exit()
            self.validate_zip()
            package_dir = self.extract()
            self.validate_extracted_package(package_dir)
            backup_info = self.backup()
            try:
                self.replace(package_dir)
                self.validate_installed_application()
            except Exception as exc:
                self.logger.exception("Failure after backup; rollback required")
                self.rollback(backup_info)
                raise
            self.launch()
            self.logger.info("Updater completed successfully")
        finally:
            self.cleanup_extracted_files()

    def validate_arguments(self) -> None:
        """Validate installer command-line arguments."""
        self.logger.info("Validating installer arguments")
        self.validator.validate_arguments(self.config)

    def wait_for_manager_exit(self) -> None:
        """Wait until ScenarioRP Manager has exited."""
        self.logger.info("Waiting for manager process: pid=%s", self.config.manager_pid)
        self.launcher.wait_for_exit(self.config.app_dir, self.config.timeout_seconds, self.config.manager_pid)

    def validate_zip(self) -> None:
        """Validate the downloaded update ZIP."""
        self.logger.info("Validating ZIP: %s", self.config.zip_path)
        self.validator.validate_zip(self.config.zip_path)

    def extract(self) -> Path:
        """Extract the update ZIP into a temporary folder."""
        self.logger.info("Extraction start")
        package_dir = self.extractor.extract(self.config.zip_path, self.config.extracted_dir)
        self.extracted_package_dir = package_dir
        self.extraction_root = self._find_extraction_root(package_dir)
        self.logger.info("Extraction completed. Package root: %s", package_dir)
        return package_dir

    def validate_extracted_package(self, package_dir: Path) -> None:
        """Validate extracted package files."""
        self.logger.info("Validating extracted package: %s", package_dir)
        self.validator.validate_extracted_package(package_dir)

    def backup(self) -> BackupInfo:
        """Create a backup of the current application files."""
        self.logger.info("Backup start")
        self.backup_info = self.backup_manager.create_backup(self.config.app_dir, self.config.backups_dir)
        self.logger.info("Backup completed: %s", self.backup_info.backup_dir)
        return self.backup_info

    def replace(self, package_dir: Path) -> ReplacementState:
        """Replace application files with extracted update files."""
        self.logger.info("Replacement start")
        removed: list[str] = []
        copied: list[str] = []
        self.replacement_started = True
        try:
            for path in iter_application_managed_paths(self.config.app_dir):
                self.logger.info("Removing old path: %s", path)
                relative = path.relative_to(self.config.app_dir).as_posix()
                remove_path(path, self.config.app_dir)
                removed.append(relative)
            for source in package_dir.iterdir():
                destination = self.config.app_dir / source.name
                self.logger.info("Copying new path: %s -> %s", source, destination)
                copy_path(source, destination, self.config.app_dir)
                copied.append(source.name)
            self.replacement_state = ReplacementState(removed_paths=tuple(removed), copied_paths=tuple(copied))
            self.logger.info("Replacement completed")
            return self.replacement_state
        except Exception as exc:
            raise UpdateReplacementError(f"Could not replace application files from {package_dir}") from exc

    def rollback(self, backup_info: BackupInfo) -> None:
        """Restore the previous version after a failed replacement."""
        self.rollback_attempted = True
        self.logger.info("Rollback start")
        self.rollback_manager.rollback(self.config.app_dir, backup_info)
        self.logger.info("Rollback result: success")

    def validate_installed_application(self) -> None:
        """Validate the installed application before launch."""
        self.logger.info("Validating installed application")
        if not self.config.manager_executable.is_file():
            raise UpdatePackageValidationError(f"Installed executable is missing: {self.config.manager_executable}")

    def launch(self) -> None:
        """Launch the updated application."""
        self.logger.info("Relaunch attempt")
        self.launcher.launch(self.config.app_dir)

    def cleanup_extracted_files(self) -> None:
        """Clean extracted update files."""
        if self.extraction_root is not None:
            self.logger.info("Cleanup extracted files: %s", self.extraction_root)
            self.extractor.cleanup(self.extraction_root)

    def _find_extraction_root(self, package_dir: Path) -> Path:
        root = package_dir
        while root.parent != self.config.extracted_dir and self.config.extracted_dir in root.parents:
            root = root.parent
        return root
