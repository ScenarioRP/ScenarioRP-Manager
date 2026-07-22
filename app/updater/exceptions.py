from __future__ import annotations


class UpdateError(Exception):
    """Base class for update system errors."""


class UpdateConfigError(UpdateError):
    """Raised when update configuration is missing or invalid."""


class UpdateCheckError(UpdateError):
    """Raised when checking for updates fails."""


class UpdateDownloadError(UpdateError):
    """Raised when downloading an update fails."""


class UpdateVersionError(UpdateError):
    """Raised when a version string cannot be parsed."""


class UpdateInstallerError(UpdateError):
    """Raised by the standalone installer architecture."""


class UpdateInstallerArgumentError(UpdateInstallerError):
    """Raised when installer command-line arguments are invalid."""


class UpdateProcessTimeoutError(UpdateInstallerError):
    """Raised when the manager process does not exit before timeout."""


class UpdateZipValidationError(UpdateInstallerError):
    """Raised when an update ZIP is missing, corrupt, unsafe, or invalid."""


class UpdateExtractionError(UpdateInstallerError):
    """Raised when extracting an update ZIP fails."""


class UpdatePackageValidationError(UpdateInstallerError):
    """Raised when extracted or installed application files are invalid."""


class UpdateBackupError(UpdateInstallerError):
    """Raised when creating a backup fails."""


class UpdateReplacementError(UpdateInstallerError):
    """Raised when replacing application files fails."""


class UpdateRollbackError(UpdateInstallerError):
    """Raised when rollback fails."""


class UpdateLaunchError(UpdateInstallerError):
    """Raised when launching ScenarioRP Manager fails."""
