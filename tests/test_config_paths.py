from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.core.config import load_config
from app.paths import AppPaths


class ConfigPathTests(unittest.TestCase):
    def test_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                """
                {
                  "fxserver_exe": "server/FXServer.exe",
                  "txdata_dir": "txData/ScenarioRP",
                  "server_cfg": "txData/ScenarioRP/server.cfg",
                  "discord_bot_dir": "discord/print_ip_server",
                  "discord_bot_python": "discord/print_ip_server/.venv/Scripts/python.exe",
                  "discord_bot_file": "discord/print_ip_server/bot.py",
                  "txadmin_profile": "default",
                  "txadmin_url": "http://127.0.0.1:40120",
                  "logs_dir": "ScenarioRP-Manager/logs",
                  "backups_dir": "backups"
                }
                """,
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.fxserver_exe, "server/FXServer.exe")

    def test_resolve_project_path(self) -> None:
        paths = AppPaths(manager_dir=Path("D:/ScenarioRP/ScenarioRP-Manager"), project_root=Path("D:/ScenarioRP"))
        self.assertEqual(paths.resolve_project_path("server/FXServer.exe"), Path("D:/ScenarioRP/server/FXServer.exe"))

    def test_app_paths_source_mode_uses_repository_root(self) -> None:
        import app.paths as paths_module

        reloaded = importlib.reload(paths_module)

        self.assertEqual(reloaded.ROOT, Path(__file__).resolve().parents[1])
        self.assertEqual(reloaded.APP, reloaded.ROOT / "app")
        self.assertEqual(reloaded.ASSETS, reloaded.ROOT / "assets")
        self.assertEqual(reloaded.SYSTEM_DATA, reloaded.ROOT / "system_data")

    def test_app_paths_frozen_mode_uses_executable_directory(self) -> None:
        import app.paths as paths_module

        with tempfile.TemporaryDirectory() as directory:
            dist_root = Path(directory) / "ScenarioRP-Manager"
            exe_path = dist_root / "ScenarioRP-Manager.exe"
            bundle_root = dist_root / "_internal"
            exe_path.parent.mkdir(parents=True)
            with mock.patch.object(sys, "frozen", True, create=True), mock.patch.object(
                sys, "executable", str(exe_path)
            ), mock.patch.object(sys, "_MEIPASS", str(bundle_root), create=True):
                reloaded = importlib.reload(paths_module)
                self.assertEqual(reloaded.ROOT, dist_root.resolve())
                self.assertEqual(reloaded.APP, bundle_root.resolve() / "app")
                self.assertEqual(reloaded.ASSETS, dist_root.resolve() / "assets")
                self.assertEqual(reloaded.SYSTEM_DATA, dist_root.resolve() / "system_data")
                self.assertEqual(reloaded.USER_DATA, dist_root.resolve() / "user_data")

        importlib.reload(paths_module)


if __name__ == "__main__":
    unittest.main()
