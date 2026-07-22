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
