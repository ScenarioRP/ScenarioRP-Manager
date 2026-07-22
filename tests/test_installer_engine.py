from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from app.updater.exceptions import (
    UpdateExtractionError,
    UpdateInstallerArgumentError,
    UpdateLaunchError,
    UpdatePackageValidationError,
    UpdateProcessTimeoutError,
    UpdateReplacementError,
    UpdateRollbackError,
    UpdateZipValidationError,
)
from app.updater.installer.backup import BackupManager
from app.updater.installer.extractor import UpdateExtractor
from app.updater.installer.installer import UpdateInstaller
from app.updater.installer.launcher import ApplicationLauncher
from app.updater.installer.rollback import RollbackManager
from app.updater.installer.validator import UpdateValidator
from app.updater.models import InstallerConfig
from app.updater.updater_main import EXIT_PROCESS_TIMEOUT, EXIT_SUCCESS, main


def logger() -> logging.Logger:
    test_logger = logging.getLogger("installer-engine-tests")
    test_logger.handlers.clear()
    test_logger.addHandler(logging.NullHandler())
    return test_logger


def write_file(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_app(app_dir: Path) -> None:
    write_file(app_dir / "ScenarioRP-Manager.exe", "old exe")
    write_file(app_dir / "old_file.txt", "old")
    write_file(app_dir / "assets" / "old_asset.txt", "old asset")
    write_file(app_dir / "user_data" / "settings.json", "keep")
    write_file(app_dir / "user_data" / "updates" / "downloads" / "download.zip", "keep zip")


def create_package(package_dir: Path, exe_content: str = "new exe") -> None:
    write_file(package_dir / "ScenarioRP-Manager.exe", exe_content)
    write_file(package_dir / "new_file.txt", "new")


def create_zip(zip_path: Path, files: dict[str, str]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def valid_root_zip(zip_path: Path) -> None:
    create_zip(
        zip_path,
        {
            "ScenarioRP-Manager.exe": "new exe",
            "new_file.txt": "new",
        },
    )


def valid_wrapper_zip(zip_path: Path) -> None:
    create_zip(
        zip_path,
        {
            "ScenarioRP-Manager-v0.2.0-Windows/ScenarioRP-Manager.exe": "new exe",
            "ScenarioRP-Manager-v0.2.0-Windows/new_file.txt": "new",
        },
    )


class FakeLauncher:
    def __init__(self) -> None:
        self.waited = False
        self.launched = False

    def wait_for_exit(self, app_dir: Path, timeout_seconds: float, manager_pid: int | None = None) -> None:
        self.waited = True

    def launch(self, app_dir: Path) -> None:
        self.launched = True


class InstallerValidationTests(unittest.TestCase):
    def test_missing_app_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = InstallerConfig(app_dir=Path(directory) / "missing", zip_path=Path(directory) / "update.zip")
            with self.assertRaises(UpdateInstallerArgumentError):
                UpdateValidator().validate_arguments(config)

    def test_missing_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            app_dir.mkdir()
            config = InstallerConfig(app_dir=app_dir, zip_path=Path(directory) / "missing.zip")
            with self.assertRaises(UpdateInstallerArgumentError):
                UpdateValidator().validate_arguments(config)

    def test_invalid_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            app_dir.mkdir()
            zip_path = Path(directory) / "update.zip"
            valid_root_zip(zip_path)
            config = InstallerConfig(app_dir=app_dir, zip_path=zip_path, timeout_seconds=0)
            with self.assertRaises(UpdateInstallerArgumentError):
                UpdateValidator().validate_arguments(config)

    def test_invalid_pid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            app_dir.mkdir()
            zip_path = Path(directory) / "update.zip"
            valid_root_zip(zip_path)
            config = InstallerConfig(app_dir=app_dir, zip_path=zip_path, manager_pid=-1)
            with self.assertRaises(UpdateInstallerArgumentError):
                UpdateValidator().validate_arguments(config)

    def test_corrupted_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "bad.zip"
            zip_path.write_text("bad", encoding="utf-8")
            with self.assertRaises(UpdateZipValidationError):
                UpdateValidator().validate_zip(zip_path)

    def test_empty_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "empty.zip"
            with zipfile.ZipFile(zip_path, "w"):
                pass
            with self.assertRaises(UpdateZipValidationError):
                UpdateValidator().validate_zip(zip_path)

    def test_zip_slip_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "unsafe.zip"
            create_zip(zip_path, {"../evil.txt": "evil", "ScenarioRP-Manager.exe": "exe"})
            with self.assertRaises(UpdateZipValidationError):
                UpdateValidator().validate_zip(zip_path)

    def test_absolute_path_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "absolute.zip"
            create_zip(zip_path, {"C:/evil.txt": "evil", "ScenarioRP-Manager.exe": "exe"})
            with self.assertRaises(UpdateZipValidationError):
                UpdateValidator().validate_zip(zip_path)

    def test_valid_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            zip_path = Path(directory) / "valid.zip"
            valid_root_zip(zip_path)
            UpdateValidator().validate_zip(zip_path)

    def test_missing_executable_in_extracted_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UpdatePackageValidationError):
                UpdateValidator().validate_extracted_package(Path(directory))


class InstallerExtractionTests(unittest.TestCase):
    def test_successful_direct_root_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = root / "update.zip"
            valid_root_zip(zip_path)
            package_root = UpdateExtractor().extract(zip_path, root / "extracted")

            self.assertTrue((package_root / "ScenarioRP-Manager.exe").is_file())

    def test_wrapper_root_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = root / "update.zip"
            valid_wrapper_zip(zip_path)
            package_root = UpdateExtractor().extract(zip_path, root / "extracted")

            self.assertEqual(package_root.name, "ScenarioRP-Manager-v0.2.0-Windows")
            self.assertTrue((package_root / "ScenarioRP-Manager.exe").is_file())

    def test_cleanup_after_extraction_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = root / "unsafe.zip"
            create_zip(zip_path, {"../evil.txt": "evil", "ScenarioRP-Manager.exe": "exe"})
            extracted_dir = root / "extracted"

            with self.assertRaises(UpdateExtractionError):
                UpdateExtractor().extract(zip_path, extracted_dir)

            self.assertFalse(any(extracted_dir.iterdir()))

    def test_unsafe_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            zip_path = root / "unsafe.zip"
            create_zip(zip_path, {"/absolute.txt": "evil", "ScenarioRP-Manager.exe": "exe"})
            with self.assertRaises(UpdateExtractionError):
                UpdateExtractor().extract(zip_path, root / "extracted")


class InstallerBackupReplacementRollbackTests(unittest.TestCase):
    def test_backup_copies_application_files_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            backup = BackupManager().create_backup(app_dir, app_dir / "user_data" / "updates" / "backups")

            self.assertTrue((backup.backup_dir / "ScenarioRP-Manager.exe").is_file())
            self.assertTrue((backup.backup_dir / "assets" / "old_asset.txt").is_file())
            self.assertFalse((backup.backup_dir / "user_data").exists())
            self.assertTrue(backup.manifest_path.is_file())
            self.assertIn("old_file.txt", backup.backed_up_paths)

    def test_backup_directory_is_unique(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            backups_dir = app_dir / "user_data" / "updates" / "backups"
            first = BackupManager().create_backup(app_dir, backups_dir)
            second = BackupManager().create_backup(app_dir, backups_dir)

            self.assertNotEqual(first.backup_dir, second.backup_dir)

    def test_updater_executable_is_excluded_from_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            write_file(app_dir / "ScenarioRPUpdater.exe", "updater")
            backup = BackupManager().create_backup(app_dir, app_dir / "user_data" / "updates" / "backups")

            self.assertFalse((backup.backup_dir / "ScenarioRPUpdater.exe").exists())

    def test_replacement_preserves_user_data_zip_and_updater_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_dir = root / "app"
            package_dir = root / "package"
            create_app(app_dir)
            create_package(package_dir)
            write_file(app_dir / "ScenarioRPUpdater.exe", "updater")
            installer = UpdateInstaller(InstallerConfig(app_dir=app_dir, zip_path=root / "update.zip"), logger=logger())

            installer.replace(package_dir)

            self.assertEqual((app_dir / "ScenarioRP-Manager.exe").read_text(encoding="utf-8"), "new exe")
            self.assertTrue((app_dir / "new_file.txt").is_file())
            self.assertFalse((app_dir / "old_file.txt").exists())
            self.assertEqual((app_dir / "user_data" / "settings.json").read_text(encoding="utf-8"), "keep")
            self.assertTrue((app_dir / "user_data" / "updates" / "downloads" / "download.zip").is_file())
            self.assertEqual((app_dir / "ScenarioRPUpdater.exe").read_text(encoding="utf-8"), "updater")

    def test_rollback_restores_old_files_and_removes_new_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_dir = root / "app"
            package_dir = root / "package"
            create_app(app_dir)
            create_package(package_dir)
            backup = BackupManager().create_backup(app_dir, app_dir / "user_data" / "updates" / "backups")
            installer = UpdateInstaller(InstallerConfig(app_dir=app_dir, zip_path=root / "update.zip"), logger=logger())
            installer.replace(package_dir)

            RollbackManager(logger()).rollback(app_dir, backup)

            self.assertEqual((app_dir / "ScenarioRP-Manager.exe").read_text(encoding="utf-8"), "old exe")
            self.assertTrue((app_dir / "old_file.txt").is_file())
            self.assertFalse((app_dir / "new_file.txt").exists())
            self.assertEqual((app_dir / "user_data" / "settings.json").read_text(encoding="utf-8"), "keep")

    def test_forced_copy_failure_triggers_rollback_in_full_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app_dir = root / "app"
            create_app(app_dir)
            zip_path = app_dir / "user_data" / "updates" / "downloads" / "update.zip"
            valid_root_zip(zip_path)
            installer = UpdateInstaller(
                InstallerConfig(app_dir=app_dir, zip_path=zip_path),
                logger=logger(),
                launcher=FakeLauncher(),
            )

            with patch("app.updater.installer.installer.copy_path", side_effect=OSError("copy failed")):
                with self.assertRaises(UpdateReplacementError):
                    installer.run()

            self.assertEqual((app_dir / "ScenarioRP-Manager.exe").read_text(encoding="utf-8"), "old exe")
            self.assertTrue((app_dir / "old_file.txt").is_file())
            self.assertEqual((app_dir / "user_data" / "settings.json").read_text(encoding="utf-8"), "keep")
            self.assertTrue(installer.rollback_attempted)

    def test_rollback_failure_raises_update_rollback_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            backup = BackupManager().create_backup(app_dir, app_dir / "user_data" / "updates" / "backups")

            with patch("app.updater.installer.rollback.copy_path", side_effect=OSError("restore failed")):
                with self.assertRaises(UpdateRollbackError):
                    RollbackManager(logger()).rollback(app_dir, backup)


class InstallerProcessLaunchFullFlowTests(unittest.TestCase):
    def test_wait_no_pid_allows_manual_testing(self) -> None:
        ApplicationLauncher(logger()).wait_for_exit(Path("unused"), timeout_seconds=1, manager_pid=None)

    def test_wait_exits_immediately_when_pid_is_gone(self) -> None:
        launcher = ApplicationLauncher(logger())
        with patch.object(launcher, "process_exists", return_value=False):
            launcher.wait_for_exit(Path("unused"), timeout_seconds=1, manager_pid=123)

    def test_waits_while_pid_exists(self) -> None:
        launcher = ApplicationLauncher(logger())
        states = iter([True, True, False])
        with patch.object(launcher, "process_exists", side_effect=lambda pid: next(states)):
            launcher.wait_for_exit(Path("unused"), timeout_seconds=1, manager_pid=123)

    def test_wait_timeout_raises(self) -> None:
        launcher = ApplicationLauncher(logger())
        with patch.object(launcher, "process_exists", return_value=True):
            with self.assertRaises(UpdateProcessTimeoutError):
                launcher.wait_for_exit(Path("unused"), timeout_seconds=0.01, manager_pid=123)

    def test_launch_uses_expected_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory)
            write_file(app_dir / "ScenarioRP-Manager.exe", "exe")
            with patch("app.updater.installer.launcher.subprocess.Popen") as popen:
                ApplicationLauncher(logger()).launch(app_dir)

            args, kwargs = popen.call_args
            self.assertEqual(args[0], [str(app_dir / "ScenarioRP-Manager.exe")])
            self.assertEqual(kwargs["cwd"], str(app_dir))
            self.assertFalse(kwargs["shell"])

    def test_launch_error_is_wrapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory)
            write_file(app_dir / "ScenarioRP-Manager.exe", "exe")
            with patch("app.updater.installer.launcher.subprocess.Popen", side_effect=OSError("launch failed")):
                with self.assertRaises(UpdateLaunchError):
                    ApplicationLauncher(logger()).launch(app_dir)

    def test_full_flow_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            zip_path = app_dir / "user_data" / "updates" / "downloads" / "update.zip"
            valid_root_zip(zip_path)
            fake_launcher = FakeLauncher()
            installer = UpdateInstaller(
                InstallerConfig(app_dir=app_dir, zip_path=zip_path),
                logger=logger(),
                launcher=fake_launcher,
            )

            installer.run()

            self.assertTrue(fake_launcher.waited)
            self.assertTrue(fake_launcher.launched)
            self.assertFalse((app_dir / "old_file.txt").exists())
            self.assertTrue((app_dir / "new_file.txt").is_file())
            self.assertEqual((app_dir / "ScenarioRP-Manager.exe").read_text(encoding="utf-8"), "new exe")
            self.assertEqual((app_dir / "user_data" / "settings.json").read_text(encoding="utf-8"), "keep")
            self.assertTrue(zip_path.is_file())
            self.assertIsNotNone(installer.backup_info)
            self.assertTrue((installer.backup_info.backup_dir / "ScenarioRP-Manager.exe").is_file())

    def test_updater_main_success_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            zip_path = app_dir / "user_data" / "updates" / "downloads" / "update.zip"
            valid_root_zip(zip_path)
            with patch("app.updater.installer.launcher.subprocess.Popen"):
                code = main(["--app", str(app_dir), "--zip", str(zip_path), "--timeout", "5"])

            self.assertEqual(code, EXIT_SUCCESS)

    def test_updater_main_timeout_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_dir = Path(directory) / "app"
            create_app(app_dir)
            zip_path = app_dir / "user_data" / "updates" / "downloads" / "update.zip"
            valid_root_zip(zip_path)
            with patch("app.updater.installer.launcher.ApplicationLauncher.process_exists", return_value=True):
                code = main(["--app", str(app_dir), "--zip", str(zip_path), "--timeout", "0.01", "--pid", "123"])

            self.assertEqual(code, EXIT_PROCESS_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
