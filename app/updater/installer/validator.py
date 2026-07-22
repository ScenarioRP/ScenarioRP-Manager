from __future__ import annotations

import os
from pathlib import Path
import zipfile

from app.updater.exceptions import (
    UpdateInstallerArgumentError,
    UpdatePackageValidationError,
    UpdateZipValidationError,
)
from app.updater.installer.filesystem import safe_archive_target
from app.updater.models import InstallerConfig

DEFAULT_MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024


class UpdateValidator:
    """Interface for validating installer inputs and update packages."""

    def __init__(self, max_uncompressed_bytes: int = DEFAULT_MAX_UNCOMPRESSED_BYTES) -> None:
        self.max_uncompressed_bytes = max_uncompressed_bytes

    def validate_arguments(self, config: InstallerConfig) -> None:
        """Validate command-line arguments that do not require update installation."""
        if not config.app_dir.exists() or not config.app_dir.is_dir():
            raise UpdateInstallerArgumentError(f"Application directory does not exist: {config.app_dir}")
        if not config.zip_path.exists() or not config.zip_path.is_file():
            raise UpdateInstallerArgumentError(f"Update ZIP does not exist: {config.zip_path}")
        if config.zip_path.suffix.lower() != ".zip":
            raise UpdateInstallerArgumentError(f"Update file must have a .zip suffix: {config.zip_path}")
        if config.timeout_seconds <= 0:
            raise UpdateInstallerArgumentError("Timeout must be greater than zero.")
        if config.manager_pid is not None and config.manager_pid <= 0:
            raise UpdateInstallerArgumentError("Manager PID must be positive when supplied.")
        self._ensure_working_directories(config)
        self._ensure_writable_directory(config.app_dir)
        self._ensure_readable_file(config.zip_path)

    def validate_zip(self, zip_path: Path) -> None:
        """Validate the downloaded update ZIP."""
        try:
            if not zipfile.is_zipfile(zip_path):
                raise UpdateZipValidationError(f"Update file is not a valid ZIP: {zip_path}")
            with zipfile.ZipFile(zip_path) as archive:
                entries = archive.infolist()
                file_entries = [entry for entry in entries if not entry.is_dir()]
                if not file_entries:
                    raise UpdateZipValidationError("Update ZIP is empty.")
                total_size = sum(entry.file_size for entry in file_entries)
                if total_size <= 0:
                    raise UpdateZipValidationError("Update ZIP contains no regular update data.")
                if total_size > self.max_uncompressed_bytes:
                    raise UpdateZipValidationError(
                        f"Update ZIP uncompressed size exceeds safety limit: {total_size} bytes"
                    )
                for entry in entries:
                    self.validate_archive_member(entry)
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise UpdateZipValidationError(f"Update ZIP contains a corrupt member: {bad_member}")
        except UpdateZipValidationError:
            raise
        except (OSError, zipfile.BadZipFile) as exc:
            raise UpdateZipValidationError(f"Could not validate update ZIP: {zip_path}") from exc

    def validate_extracted_package(self, package_dir: Path) -> None:
        """Validate extracted update files."""
        executable = (package_dir / "ScenarioRP-Manager.exe").resolve()
        try:
            executable.relative_to(package_dir.resolve())
        except ValueError as exc:
            raise UpdatePackageValidationError("ScenarioRP-Manager.exe resolves outside the package directory.") from exc
        if not executable.is_file():
            raise UpdatePackageValidationError("Extracted package is missing ScenarioRP-Manager.exe.")

    def validate_archive_member(self, entry: zipfile.ZipInfo) -> None:
        """Validate one archive member before extraction."""
        from app.updater.installer.filesystem import archive_member_is_regular_or_directory, archive_member_is_symlink

        if archive_member_is_symlink(entry):
            raise UpdateZipValidationError(f"Update ZIP contains an unsafe symlink: {entry.filename}")
        if not archive_member_is_regular_or_directory(entry):
            raise UpdateZipValidationError(f"Update ZIP contains an unsafe special file: {entry.filename}")
        try:
            safe_archive_target(Path("extract-root"), entry.filename)
        except ValueError as exc:
            raise UpdateZipValidationError(str(exc)) from exc

    def _ensure_working_directories(self, config: InstallerConfig) -> None:
        for directory in (config.updates_dir, config.downloads_dir, config.extracted_dir, config.backups_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise UpdateInstallerArgumentError(f"Could not create updater directory: {directory}") from exc

    def _ensure_writable_directory(self, directory: Path) -> None:
        if not os.access(directory, os.W_OK):
            raise UpdateInstallerArgumentError(f"Application directory is not writable: {directory}")

    def _ensure_readable_file(self, path: Path) -> None:
        try:
            with path.open("rb"):
                pass
        except OSError as exc:
            raise UpdateInstallerArgumentError(f"Update ZIP is not readable: {path}") from exc
