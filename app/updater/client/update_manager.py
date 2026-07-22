from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.updater.client.downloader import UpdateDownloader
from app.updater.client.release_provider import GitHubReleaseProvider
from app.updater.client.version import APP_VERSION, is_newer_version
from app.updater.exceptions import UpdateConfigError
from app.updater.models import UpdateRelease


@dataclass(frozen=True)
class UpdateConfig:
    """Configuration for the update system."""

    provider: str
    repository: str
    allow_prerelease: bool
    check_on_startup: bool
    request_timeout_seconds: int


class UpdateManager:
    """Coordinates update checks and update downloads."""

    def __init__(
        self,
        provider: GitHubReleaseProvider,
        downloader: UpdateDownloader,
        current_version: str = APP_VERSION,
    ) -> None:
        self.provider = provider
        self.downloader = downloader
        self.current_version = current_version

    def check_for_update(self) -> UpdateRelease | None:
        """Return an available update release, or None when current."""
        release = self.provider.get_latest_release()
        if is_newer_version(self.current_version, release.version):
            return release
        return None

    def download_update(
        self,
        release: UpdateRelease,
        destination_directory: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download the release asset into destination_directory."""
        destination = Path(destination_directory) / release.file_name
        return self.downloader.download(release.download_url, destination, progress_callback)


def load_update_config(path: Path) -> UpdateConfig:
    """Load and validate update configuration from JSON."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except OSError as exc:
        raise UpdateConfigError(f"Could not read update config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UpdateConfigError(f"Update config is not valid JSON: {path}") from exc

    if not isinstance(raw, dict):
        raise UpdateConfigError("Update config must contain a JSON object.")

    required_fields = {
        "provider",
        "repository",
        "allow_prerelease",
        "check_on_startup",
        "request_timeout_seconds",
    }
    missing = sorted(field for field in required_fields if field not in raw)
    if missing:
        raise UpdateConfigError(f"Update config is missing required field(s): {', '.join(missing)}")

    provider = raw["provider"]
    repository = raw["repository"]
    allow_prerelease = raw["allow_prerelease"]
    check_on_startup = raw["check_on_startup"]
    request_timeout_seconds = raw["request_timeout_seconds"]

    if provider != "github":
        raise UpdateConfigError("Only the 'github' update provider is supported.")
    if not isinstance(repository, str) or "/" not in repository:
        raise UpdateConfigError("Update repository must use the format 'username/repository'.")
    if not isinstance(allow_prerelease, bool):
        raise UpdateConfigError("Update allow_prerelease must be a boolean.")
    if not isinstance(check_on_startup, bool):
        raise UpdateConfigError("Update check_on_startup must be a boolean.")
    if not isinstance(request_timeout_seconds, int) or request_timeout_seconds <= 0:
        raise UpdateConfigError("Update request_timeout_seconds must be a positive integer.")

    return UpdateConfig(
        provider=provider,
        repository=repository,
        allow_prerelease=allow_prerelease,
        check_on_startup=check_on_startup,
        request_timeout_seconds=request_timeout_seconds,
    )
