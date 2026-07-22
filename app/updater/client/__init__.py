from __future__ import annotations

from app.updater.client.downloader import UpdateDownloader
from app.updater.client.release_provider import GitHubReleaseProvider
from app.updater.client.update_manager import UpdateConfig, UpdateManager, load_update_config
from app.updater.client.version import APP_VERSION, is_newer_version

__all__ = [
    "APP_VERSION",
    "GitHubReleaseProvider",
    "UpdateConfig",
    "UpdateDownloader",
    "UpdateManager",
    "is_newer_version",
    "load_update_config",
]
