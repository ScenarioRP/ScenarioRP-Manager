from __future__ import annotations

import re
from typing import Any

import requests

from app.updater.exceptions import UpdateCheckError
from app.updater.models import UpdateRelease


class GitHubReleaseProvider:
    """Reads update metadata from public GitHub Releases."""

    API_ROOT = "https://api.github.com/repos"
    USER_AGENT = "ScenarioRP-Manager-Updater/0.1"

    def __init__(self, repository: str, allow_prerelease: bool = False, timeout_seconds: int = 15) -> None:
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
            raise UpdateCheckError("GitHub repository must use the format 'username/repository'.")
        if timeout_seconds <= 0:
            raise UpdateCheckError("GitHub request timeout must be greater than zero.")

        self.repository = repository
        self.allow_prerelease = allow_prerelease
        self.timeout_seconds = timeout_seconds

    def get_latest_release(self) -> UpdateRelease:
        """Fetch the newest eligible GitHub release."""
        releases = self._fetch_releases()
        for release in releases:
            if not isinstance(release, dict):
                continue
            if release.get("draft"):
                continue
            if release.get("prerelease") and not self.allow_prerelease:
                continue

            asset = self._select_windows_zip_asset(release)
            if asset is None:
                continue

            return self._to_update_release(release, asset)

        raise UpdateCheckError("No eligible GitHub release with a Windows ZIP asset was found.")

    def _fetch_releases(self) -> list[dict[str, Any]]:
        url = f"{self.API_ROOT}/{self.repository}/releases"
        try:
            response = requests.get(
                url,
                headers={"Accept": "application/vnd.github+json", "User-Agent": self.USER_AGENT},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise UpdateCheckError(f"GitHub release request failed: {exc}") from exc
        except ValueError as exc:
            raise UpdateCheckError("GitHub release response was not valid JSON.") from exc

        if not isinstance(payload, list):
            raise UpdateCheckError("GitHub release response did not contain a release list.")

        return payload

    def _select_windows_zip_asset(self, release: dict[str, Any]) -> dict[str, Any] | None:
        assets = release.get("assets")
        if not isinstance(assets, list):
            return None

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "")
            if not name.lower().endswith(".zip"):
                continue
            if self._is_windows_asset_name(name):
                return asset

        return None

    def _to_update_release(self, release: dict[str, Any], asset: dict[str, Any]) -> UpdateRelease:
        version = str(release.get("tag_name") or "").strip()
        download_url = str(asset.get("browser_download_url") or "").strip()
        file_name = str(asset.get("name") or "").strip()
        if not version:
            raise UpdateCheckError("GitHub release is missing tag_name.")
        if not download_url:
            raise UpdateCheckError("GitHub release asset is missing browser_download_url.")
        if not file_name:
            raise UpdateCheckError("GitHub release asset is missing name.")

        release_notes = release.get("body")
        checksum = asset.get("digest")
        return UpdateRelease(
            version=version,
            download_url=download_url,
            file_name=file_name,
            release_notes=release_notes if isinstance(release_notes, str) else None,
            checksum=checksum if isinstance(checksum, str) else None,
            is_prerelease=bool(release.get("prerelease")),
        )

    def _is_windows_asset_name(self, file_name: str) -> bool:
        tokens = re.split(r"[-_.\s]+", file_name.lower())
        return any(token in {"win", "win32", "win64", "windows", "windows32", "windows64"} for token in tokens)
