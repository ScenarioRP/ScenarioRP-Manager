from __future__ import annotations

from pathlib import Path

from app.updater.exceptions import UpdateInstallerArgumentError
from app.updater.models import InstallerConfig


class UpdateValidator:
    """Interface for validating installer inputs and update packages."""

    def validate_arguments(self, config: InstallerConfig) -> None:
        """Validate command-line arguments that do not require update installation."""
        if not config.app_dir.exists() or not config.app_dir.is_dir():
            raise UpdateInstallerArgumentError(f"Application directory does not exist: {config.app_dir}")
        if not config.zip_path.exists() or not config.zip_path.is_file():
            raise UpdateInstallerArgumentError(f"Update ZIP does not exist: {config.zip_path}")
        if config.timeout_seconds <= 0:
            raise UpdateInstallerArgumentError("Timeout must be greater than zero.")

    def validate_zip(self, zip_path: Path) -> None:
        """Validate the downloaded update ZIP."""
        raise NotImplementedError("ZIP validation is not implemented yet.")

    def validate_extracted_package(self, package_dir: Path) -> None:
        """Validate extracted update files."""
        raise NotImplementedError("Extracted package validation is not implemented yet.")
