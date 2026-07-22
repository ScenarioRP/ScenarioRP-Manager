from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import requests

from app.updater.client import (
    GitHubReleaseProvider,
    UpdateDownloader,
    UpdateManager,
    is_newer_version,
)
from app.updater.exceptions import UpdateCheckError, UpdateDownloadError, UpdateVersionError
from app.updater.models import UpdateRelease


class FakeResponse:
    def __init__(
        self,
        payload: Any = None,
        chunks: list[bytes] | None = None,
        status_error: requests.RequestException | None = None,
        headers: dict[str, str] | None = None,
        chunk_error: requests.RequestException | None = None,
    ) -> None:
        self.payload = payload
        self.chunks = chunks or []
        self.status_error = status_error
        self.headers = headers or {}
        self.chunk_error = chunk_error
        self.closed = False
        self.on_iter_content: Any = None

    def raise_for_status(self) -> None:
        if self.status_error is not None:
            raise self.status_error

    def json(self) -> Any:
        return self.payload

    def iter_content(self, chunk_size: int) -> Any:
        if self.on_iter_content is not None:
            self.on_iter_content()
        for chunk in self.chunks:
            yield chunk
        if self.chunk_error is not None:
            raise self.chunk_error

    def close(self) -> None:
        self.closed = True


class StaticProvider:
    def __init__(self, release: UpdateRelease) -> None:
        self.release = release

    def get_latest_release(self) -> UpdateRelease:
        return self.release


class StaticDownloader:
    def __init__(self, path: Path) -> None:
        self.path = path

    def download(self, url: str, destination: Path, progress_callback: Any = None) -> Path:
        return self.path


class VersionTests(unittest.TestCase):
    def test_newer_version(self) -> None:
        self.assertTrue(is_newer_version("0.1.0", "0.1.1"))

    def test_newer_version_with_v_prefix(self) -> None:
        self.assertTrue(is_newer_version("0.1.0", "v0.1.1"))

    def test_prerelease_version(self) -> None:
        self.assertTrue(is_newer_version("0.9.0", "1.0.0-beta"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0-beta"))

    def test_invalid_version_raises(self) -> None:
        with self.assertRaises(UpdateVersionError):
            is_newer_version("0.1.0", "not a version")


class UpdateManagerTests(unittest.TestCase):
    def test_check_for_update_returns_none_when_current(self) -> None:
        release = UpdateRelease("0.1.0", "https://example.test/app.zip", "app.zip", None, None, False)
        manager = UpdateManager(StaticProvider(release), StaticDownloader(Path("unused")), current_version="0.1.0")

        self.assertIsNone(manager.check_for_update())

    def test_check_for_update_returns_release_when_newer(self) -> None:
        release = UpdateRelease("0.2.0", "https://example.test/app.zip", "app.zip", None, None, False)
        manager = UpdateManager(StaticProvider(release), StaticDownloader(Path("unused")), current_version="0.1.0")

        self.assertEqual(manager.check_for_update(), release)


class GitHubReleaseProviderTests(unittest.TestCase):
    def test_selects_windows_zip_asset(self) -> None:
        payload = [
            {
                "tag_name": "v0.2.0",
                "draft": False,
                "prerelease": False,
                "body": "notes",
                "assets": [
                    {"name": "ScenarioRP-linux.zip", "browser_download_url": "https://example.test/linux.zip"},
                    {"name": "ScenarioRP-Windows.zip", "browser_download_url": "https://example.test/windows.zip"},
                ],
            }
        ]
        response = FakeResponse(payload=payload)

        with patch("app.updater.client.release_provider.requests.get", return_value=response):
            release = GitHubReleaseProvider("owner/repo").get_latest_release()

        self.assertEqual(release.version, "v0.2.0")
        self.assertEqual(release.file_name, "ScenarioRP-Windows.zip")
        self.assertEqual(release.download_url, "https://example.test/windows.zip")
        self.assertEqual(release.release_notes, "notes")

    def test_network_failure_raises_update_check_error(self) -> None:
        with patch(
            "app.updater.client.release_provider.requests.get",
            side_effect=requests.Timeout("timed out"),
        ):
            with self.assertRaises(UpdateCheckError):
                GitHubReleaseProvider("owner/repo").get_latest_release()


class UpdateDownloaderTests(unittest.TestCase):
    def test_download_creates_part_file_then_final_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "ScenarioRP-Windows.zip"
            part_path = destination.with_name(f"{destination.name}.part")
            response = FakeResponse(chunks=[b"abc", b"def"], headers={"Content-Length": "6"})
            saw_part_file = False

            def on_iter_content() -> None:
                nonlocal saw_part_file
                saw_part_file = part_path.exists()

            response.on_iter_content = on_iter_content
            progress: list[tuple[int, int]] = []

            with patch("app.updater.client.downloader.requests.get", return_value=response):
                result = UpdateDownloader().download(
                    "https://example.test/ScenarioRP-Windows.zip",
                    destination,
                    lambda downloaded, total: progress.append((downloaded, total)),
                )

            self.assertEqual(result, destination)
            self.assertTrue(saw_part_file)
            self.assertTrue(destination.exists())
            self.assertFalse(part_path.exists())
            self.assertEqual(destination.read_bytes(), b"abcdef")
            self.assertEqual(progress[-1], (6, 6))

    def test_download_removes_partial_file_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "ScenarioRP-Windows.zip"
            part_path = destination.with_name(f"{destination.name}.part")
            response = FakeResponse(
                chunks=[b"abc"],
                headers={"Content-Length": "6"},
                chunk_error=requests.ConnectionError("connection lost"),
            )

            with patch("app.updater.client.downloader.requests.get", return_value=response):
                with self.assertRaises(UpdateDownloadError):
                    UpdateDownloader().download("https://example.test/ScenarioRP-Windows.zip", destination)

            self.assertFalse(destination.exists())
            self.assertFalse(part_path.exists())


if __name__ == "__main__":
    unittest.main()
