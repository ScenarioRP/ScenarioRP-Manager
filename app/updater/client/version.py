from __future__ import annotations

from packaging.version import InvalidVersion, Version

from app.updater.exceptions import UpdateVersionError


APP_VERSION = "0.1.1"


def is_newer_version(current_version: str, latest_version: str) -> bool:
    """Return True when latest_version is newer than current_version."""
    try:
        current = Version(_normalize_version(current_version))
        latest = Version(_normalize_version(latest_version))
    except InvalidVersion as exc:
        raise UpdateVersionError(f"Invalid version string: {exc}") from exc

    return latest > current


def _normalize_version(version: str) -> str:
    return version.strip().removeprefix("v").removeprefix("V")
