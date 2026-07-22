from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateRelease:
    """Metadata for an available application update."""

    version: str
    download_url: str
    file_name: str
    release_notes: str | None
    checksum: str | None
    is_prerelease: bool


@dataclass(frozen=True)
class InstallerConfig:
    """Command-line configuration for the future standalone updater executable."""

    app_dir: Path
    zip_path: Path
    timeout_seconds: float = 120.0
