from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _distribution_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[1]


def _bundle_root(distribution_root: Path) -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
        return distribution_root

    return distribution_root


def _user_data_root(root: Path) -> Path:
    configured = os.environ.get("SCENARIORP_MANAGER_USER_DATA")
    if configured:
        return Path(configured).expanduser().resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "user_data"

    return root / "user_data"


ROOT = _distribution_root()
BUNDLE_ROOT = _bundle_root(ROOT)
APP = BUNDLE_ROOT / "app"
ASSETS = ROOT / "assets"
SYSTEM_DATA = ROOT / "system_data"
USER_DATA = _user_data_root(ROOT)
UPDATE_CONFIG = SYSTEM_DATA / "update_config.json"
UPDATES = USER_DATA / "updates"
UPDATE_DOWNLOADS = UPDATES / "downloads"
UPDATE_EXTRACTED = UPDATES / "extracted"
UPDATE_BACKUP = UPDATES / "backups"


@dataclass(frozen=True)
class AppPaths:
    manager_dir: Path
    project_root: Path
    app_dir: Path | None = None
    assets_dir: Path | None = None
    system_data_dir: Path | None = None
    user_data_dir: Path | None = None

    def __post_init__(self) -> None:
        manager_dir = Path(self.manager_dir)
        object.__setattr__(self, "manager_dir", manager_dir)
        object.__setattr__(self, "project_root", Path(self.project_root))
        object.__setattr__(self, "app_dir", Path(self.app_dir) if self.app_dir is not None else manager_dir / "app")
        object.__setattr__(
            self,
            "assets_dir",
            Path(self.assets_dir) if self.assets_dir is not None else manager_dir / "assets",
        )
        object.__setattr__(
            self,
            "system_data_dir",
            Path(self.system_data_dir) if self.system_data_dir is not None else manager_dir / "system_data",
        )
        object.__setattr__(
            self,
            "user_data_dir",
            Path(self.user_data_dir) if self.user_data_dir is not None else manager_dir / "user_data",
        )

    @classmethod
    def discover(cls) -> "AppPaths":
        project_root = Path(os.environ.get("SCENARIORP_PROJECT_ROOT", ROOT.parent)).expanduser().resolve()
        paths = cls(
            manager_dir=ROOT,
            project_root=project_root,
            app_dir=APP,
            assets_dir=ASSETS,
            system_data_dir=SYSTEM_DATA,
            user_data_dir=USER_DATA,
        )
        paths.ensure_directories()
        return paths

    @property
    def root(self) -> Path:
        return self.manager_dir

    @property
    def app(self) -> Path:
        return self.app_dir or self.manager_dir / "app"

    @property
    def assets(self) -> Path:
        return self.assets_dir or self.manager_dir / "assets"

    @property
    def system_data(self) -> Path:
        return self.system_data_dir or self.manager_dir / "system_data"

    @property
    def user_data(self) -> Path:
        return self.user_data_dir or self.manager_dir / "user_data"

    def ensure_directories(self) -> None:
        for directory in (
            self.assets,
            self.system_data,
            self.user("logs"),
            self.user("cache"),
            self.user("saves"),
            self.user("state"),
            self.update_downloads,
            self.update_extracted,
            self.update_backup,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def asset(self, *parts: str | Path) -> Path:
        return self.assets.joinpath(*parts)

    def system(self, *parts: str | Path) -> Path:
        return self.system_data.joinpath(*parts)

    def user(self, *parts: str | Path) -> Path:
        return self.user_data.joinpath(*parts)

    def app_file(self, *parts: str | Path) -> Path:
        return self.app.joinpath(*parts)

    @property
    def update_config(self) -> Path:
        return self.system("update_config.json")

    @property
    def updates(self) -> Path:
        return self.user("updates")

    @property
    def update_downloads(self) -> Path:
        return self.updates / "downloads"

    @property
    def update_extracted(self) -> Path:
        return self.updates / "extracted"

    @property
    def update_backup(self) -> Path:
        return self.updates / "backups"

    def resolve_project_path(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def script_environment(self) -> Mapping[str, str]:
        return {
            "SCENARIORP_MANAGER_ROOT": str(self.manager_dir),
            "SCENARIORP_MANAGER_APP": str(self.app),
            "SCENARIORP_MANAGER_ASSETS": str(self.assets),
            "SCENARIORP_MANAGER_SYSTEM_DATA": str(self.system_data),
            "SCENARIORP_MANAGER_USER_DATA": str(self.user_data),
            "SCENARIORP_MANAGER_PROJECT_ROOT": str(self.project_root),
        }
