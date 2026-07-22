from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.updater.client import APP_VERSION, GitHubReleaseProvider, UpdateDownloader, UpdateManager
from app.updater.installer import (
    ApplicationLauncher,
    BackupManager,
    RollbackManager,
    UpdateExtractor,
    UpdateInstaller,
    UpdateValidator,
)
from app.updater.models import InstallerConfig
from app.updater.updater_main import parse_args


class UpdaterArchitectureTests(unittest.TestCase):
    def test_client_imports_are_available_from_client_package(self) -> None:
        self.assertEqual(APP_VERSION, "0.1.1")
        self.assertIs(GitHubReleaseProvider, GitHubReleaseProvider)
        self.assertIs(UpdateDownloader, UpdateDownloader)
        self.assertIs(UpdateManager, UpdateManager)

    def test_updater_main_parses_arguments(self) -> None:
        config = parse_args(["--app", "C:/ScenarioRP", "--zip", "C:/ScenarioRP/update.zip", "--timeout", "30"])

        self.assertEqual(config.app_dir, Path("C:/ScenarioRP"))
        self.assertEqual(config.zip_path, Path("C:/ScenarioRP/update.zip"))
        self.assertEqual(config.timeout_seconds, 30.0)

    def test_installer_classes_can_be_instantiated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = InstallerConfig(app_dir=Path(directory), zip_path=Path(directory) / "update.zip")

            self.assertIsInstance(UpdateValidator(), UpdateValidator)
            self.assertIsInstance(UpdateExtractor(), UpdateExtractor)
            self.assertIsInstance(BackupManager(), BackupManager)
            self.assertIsInstance(RollbackManager(), RollbackManager)
            self.assertIsInstance(ApplicationLauncher(), ApplicationLauncher)
            self.assertIsInstance(UpdateInstaller(config), UpdateInstaller)

    def test_installer_flow_methods_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = InstallerConfig(app_dir=Path(directory), zip_path=Path(directory) / "update.zip")
            installer = UpdateInstaller(config)

            for method_name in (
                "validate_arguments",
                "wait_for_manager_exit",
                "validate_zip",
                "extract",
                "backup",
                "replace",
                "rollback",
                "launch",
                "run",
            ):
                self.assertTrue(callable(getattr(installer, method_name)))


if __name__ == "__main__":
    unittest.main()
