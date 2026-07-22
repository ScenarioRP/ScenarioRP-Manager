from __future__ import annotations

from app.updater.installer.backup import BackupManager
from app.updater.installer.extractor import UpdateExtractor
from app.updater.installer.launcher import ApplicationLauncher
from app.updater.installer.rollback import RollbackManager
from app.updater.installer.validator import UpdateValidator
from app.updater.models import InstallerConfig


class UpdateInstaller:
    """Defines the future standalone updater installation flow."""

    def __init__(
        self,
        config: InstallerConfig,
        validator: UpdateValidator | None = None,
        extractor: UpdateExtractor | None = None,
        backup_manager: BackupManager | None = None,
        rollback_manager: RollbackManager | None = None,
        launcher: ApplicationLauncher | None = None,
    ) -> None:
        self.config = config
        self.validator = validator or UpdateValidator()
        self.extractor = extractor or UpdateExtractor()
        self.backup_manager = backup_manager or BackupManager()
        self.rollback_manager = rollback_manager or RollbackManager()
        self.launcher = launcher or ApplicationLauncher()

    def run(self) -> None:
        """Run the future install flow.

        Planned flow:
        validate arguments -> wait for manager exit -> validate zip -> extract ->
        backup -> replace -> rollback if needed -> launch application.
        """
        self.validate_arguments()
        self.wait_for_manager_exit()
        self.validate_zip()
        self.extract()
        self.backup()
        try:
            self.replace()
        except Exception:
            self.rollback()
            raise
        self.launch()

    def validate_arguments(self) -> None:
        """Validate installer command-line arguments."""
        self.validator.validate_arguments(self.config)

    def wait_for_manager_exit(self) -> None:
        """Wait until ScenarioRP Manager has exited."""
        self.launcher.wait_for_exit(self.config.app_dir, self.config.timeout_seconds)

    def validate_zip(self) -> None:
        """Validate the downloaded update ZIP."""
        self.validator.validate_zip(self.config.zip_path)

    def extract(self) -> None:
        """Extract the update ZIP into a temporary folder."""
        self.extractor.extract(self.config.zip_path)

    def backup(self) -> None:
        """Create a backup of the current application files."""
        self.backup_manager.create_backup(self.config.app_dir)

    def replace(self) -> None:
        """Replace application files with extracted update files."""
        raise NotImplementedError("File replacement is not implemented yet.")

    def rollback(self) -> None:
        """Restore the previous version after a failed replacement."""
        self.rollback_manager.rollback(self.config.app_dir)

    def launch(self) -> None:
        """Launch the updated application."""
        self.launcher.launch(self.config.app_dir)
