from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.config import load_config
from core.paths import AppPaths


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
                  "discord_bot_dir": "ScenarioRP-Discord-Bots/Server-Status",
                  "discord_bot_python": "ScenarioRP-Discord-Bots/Server-Status/.venv/Scripts/python.exe",
                  "discord_bot_file": "ScenarioRP-Discord-Bots/Server-Status/bot.py",
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


if __name__ == "__main__":
    unittest.main()
