from __future__ import annotations

from pathlib import Path
from typing import Callable

import requests

from app.updater.exceptions import UpdateDownloadError


class UpdateDownloader:
    """Downloads update files safely using a temporary partial file."""

    USER_AGENT = "ScenarioRP-Manager-Updater/0.1"

    def __init__(self, timeout_seconds: int = 15, chunk_size: int = 1024 * 1024) -> None:
        if timeout_seconds <= 0:
            raise UpdateDownloadError("Download timeout must be greater than zero.")
        if chunk_size <= 0:
            raise UpdateDownloadError("Download chunk size must be greater than zero.")

        self.timeout_seconds = timeout_seconds
        self.chunk_size = chunk_size

    def download(
        self,
        url: str,
        destination: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download url to destination and return the completed file path."""
        destination = Path(destination)
        part_path = destination.with_name(f"{destination.name}.part")
        destination.parent.mkdir(parents=True, exist_ok=True)

        response: requests.Response | None = None
        bytes_downloaded = 0
        total_bytes = 0
        try:
            response = requests.get(
                url,
                headers={"User-Agent": self.USER_AGENT},
                stream=True,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            total_bytes = self._content_length(response)

            with part_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback is not None:
                        progress_callback(bytes_downloaded, total_bytes)

            if bytes_downloaded == 0:
                raise UpdateDownloadError("Downloaded update file was empty.")

            part_path.replace(destination)
            return destination
        except UpdateDownloadError:
            self._remove_partial_file(part_path)
            raise
        except (OSError, requests.RequestException) as exc:
            self._remove_partial_file(part_path)
            raise UpdateDownloadError(f"Update download failed: {exc}") from exc
        finally:
            if response is not None:
                response.close()

    def _content_length(self, response: requests.Response) -> int:
        value = response.headers.get("Content-Length")
        if value is None:
            return 0
        try:
            return int(value)
        except ValueError:
            return 0

    def _remove_partial_file(self, part_path: Path) -> None:
        try:
            part_path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise UpdateDownloadError(f"Could not remove partial update file: {part_path}") from exc
