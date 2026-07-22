from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication

from app.core.config import AppConfig
from app.paths import AppPaths
from app.ui.main_window import MainWindow
from app.ui.update import UpdateDialog, UpdateDownloadWorker
from app.updater import UpdateRelease
from app.updater.version import APP_VERSION


def _qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeDownloadManager:
    def __init__(self, path: Path) -> None:
        self.path = path

    def download_update(self, release: UpdateRelease, destination_directory: Path, progress_callback: object = None) -> Path:
        if progress_callback is not None:
            progress_callback(5, 10)
        return self.path


class UpdateUiTests(unittest.TestCase):
    def setUp(self) -> None:
        _qapp()

    def _config(self) -> AppConfig:
        return AppConfig(
            fxserver_exe="server/FXServer.exe",
            txdata_dir="txData/ScenarioRP",
            server_cfg="txData/ScenarioRP/server.cfg",
            discord_bot_dir="discord/print_ip_server",
            discord_bot_python="discord/print_ip_server/.venv/Scripts/python.exe",
            discord_bot_file="discord/print_ip_server/bot.py",
            txadmin_profile="default",
            txadmin_url="http://127.0.0.1:40120",
            logs_dir="ScenarioRP-Manager/logs",
            backups_dir="backups",
        )

    def _paths(self, directory: str, check_on_startup: bool = False) -> AppPaths:
        root = Path.cwd()
        system_data = Path(directory) / "system_data"
        user_data = Path(directory) / "user_data"
        system_data.mkdir(parents=True, exist_ok=True)
        (system_data / "update_config.json").write_text(
            f"""
            {{
              "provider": "github",
              "repository": "ScenarioRP/ScenarioRP-Manager",
              "allow_prerelease": false,
              "check_on_startup": {str(check_on_startup).lower()},
              "request_timeout_seconds": 15
            }}
            """,
            encoding="utf-8",
        )
        paths = AppPaths(
            manager_dir=root,
            project_root=root.parent,
            app_dir=root / "app",
            assets_dir=root / "assets",
            system_data_dir=system_data,
            user_data_dir=user_data,
        )
        paths.ensure_directories()
        return paths

    def _window(self, paths: AppPaths) -> MainWindow:
        with (
            patch.object(MainWindow, "_setup_txadmin_view", lambda self: None),
            patch.object(MainWindow, "refresh_status", lambda self: None),
            patch("app.ui.main_window.QTimer.singleShot", lambda *args: None),
        ):
            return MainWindow(config=self._config(), paths=paths)

    def _release(self) -> UpdateRelease:
        return UpdateRelease(
            version="0.2.0",
            download_url="https://example.test/ScenarioRP-Windows.zip",
            file_name="ScenarioRP-Windows.zip",
            release_notes="Release notes",
            checksum=None,
            is_prerelease=False,
        )

    def test_startup_check_does_not_run_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = self._window(self._paths(directory, check_on_startup=False))
            window._start_update_check = MagicMock()

            window._maybe_check_for_updates_on_startup()

            window._start_update_check.assert_not_called()
            window.close()

    def test_settings_displays_app_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = self._window(self._paths(directory))

            self.assertEqual(window.settings_version_label.text(), f"Version: v{APP_VERSION}")
            window.close()

    def test_update_dialog_opens_when_release_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = self._window(self._paths(directory))

            window._update_available(self._release())

            self.assertIsInstance(window._update_dialog, UpdateDialog)
            self.assertEqual(window._update_dialog.release.version, "0.2.0")
            window._update_dialog.close()
            window.close()

    def test_no_dialog_opens_when_no_update_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch("app.ui.main_window.QMessageBox.information") as message:
            window = self._window(self._paths(directory))

            window._no_update_available()

            self.assertIsNone(window._update_dialog)
            message.assert_not_called()
            window.close()

    def test_update_check_error_does_not_crash_main_window(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch("app.ui.main_window.QMessageBox.warning") as warning:
            window = self._window(self._paths(directory))

            window._update_check_error("network failed")

            warning.assert_not_called()
            window.close()

    def test_download_worker_progress_callback_emits_signal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = self._release()
            completed: list[Path] = []
            progress: list[tuple[int, int, int]] = []
            worker = UpdateDownloadWorker(FakeDownloadManager(Path(directory) / "update.zip"), release, Path(directory))
            worker.progress.connect(lambda downloaded, total, percent: progress.append((downloaded, total, percent)))
            worker.completed.connect(lambda path: completed.append(path))

            worker.run()

            self.assertEqual(progress, [(5, 10, 50)])
            self.assertEqual(completed, [Path(directory) / "update.zip"])

    def test_download_worker_success_returns_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            release = self._release()
            completed: list[Path] = []
            expected = Path(directory) / "ScenarioRP-Windows.zip"
            worker = UpdateDownloadWorker(FakeDownloadManager(expected), release, Path(directory))
            worker.completed.connect(lambda path: completed.append(path))

            worker.run()

            self.assertEqual(completed, [expected])

    def test_update_dialog_prevents_double_download_start(self) -> None:
        dialog = UpdateDialog("0.1.0", self._release())
        requests: list[UpdateRelease] = []
        dialog.download_requested.connect(lambda release: requests.append(release))

        dialog._request_download()
        dialog._request_download()

        self.assertEqual(len(requests), 1)
        self.assertTrue(dialog.download_in_progress)
        self.assertFalse(dialog.download_button.isEnabled())
        dialog._download_in_progress = False
        dialog.close()

    def test_threads_are_cleared_after_finish_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            window = self._window(self._paths(directory))
            window._update_check_thread = object()
            window._update_check_worker = object()
            window._update_download_thread = object()
            window._update_download_worker = object()

            window._update_check_finished()
            window._download_finished()

            self.assertIsNone(window._update_check_thread)
            self.assertIsNone(window._update_check_worker)
            self.assertIsNone(window._update_download_thread)
            self.assertIsNone(window._update_download_worker)
            self.assertTrue(window.check_updates_button.isEnabled())
            window.close()


if __name__ == "__main__":
    unittest.main()
