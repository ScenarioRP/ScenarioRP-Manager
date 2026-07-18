from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import socket
import subprocess
from typing import Any
from urllib.parse import urlparse

from core.config import AppConfig
from core.paths import AppPaths


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    state: str
    message: str


@dataclass(frozen=True)
class SystemStatus:
    environment: ComponentStatus
    server: ComponentStatus
    fxserver: ComponentStatus
    discord_bot: ComponentStatus
    txadmin: ComponentStatus
    database: ComponentStatus


class ProcessMonitor:
    def __init__(self, config: AppConfig, paths: AppPaths) -> None:
        self.config = config
        self.paths = paths
        self.state_dir = paths.manager_dir / "state"
        self.fx_pid_file = self.state_dir / "fxserver.pid"
        self.bot_pid_file = self.state_dir / "discord-bot.pid"

        self.fxserver_exe = paths.resolve_project_path(config.fxserver_exe)
        self.txdata_dir = paths.resolve_project_path(config.txdata_dir)
        self.server_cfg = paths.resolve_project_path(config.server_cfg)
        self.bot_dir = paths.resolve_project_path(config.discord_bot_dir)
        self.bot_python = paths.resolve_project_path(config.discord_bot_python)
        self.bot_file = paths.resolve_project_path(config.discord_bot_file)

        txadmin = urlparse(config.txadmin_url)
        self.txadmin_host = txadmin.hostname or "127.0.0.1"
        self.txadmin_port = txadmin.port or (443 if txadmin.scheme == "https" else 80)

    def collect(self) -> SystemStatus:
        return SystemStatus(
            environment=self.environment_status(),
            server=self.server_status(),
            fxserver=self.fxserver_status(),
            discord_bot=self.discord_bot_status(),
            txadmin=self.txadmin_status(),
            database=self.database_status(),
        )

    def environment_status(self) -> ComponentStatus:
        checks = [
            ("FXServer.exe", self.fxserver_exe),
            ("txData profile", self.txdata_dir),
            ("server.cfg", self.server_cfg),
            ("Discord bot directory", self.bot_dir),
            ("Discord bot Python", self.bot_python),
            ("Discord bot file", self.bot_file),
        ]
        missing = [name for name, path in checks if not path.exists()]
        if missing:
            return ComponentStatus("Environment", "Error", f"Missing: {', '.join(missing)}")
        return ComponentStatus("Environment", "OK", "All required paths exist")

    def fxserver_status(self) -> ComponentStatus:
        return self._managed_process_status(
            name="FXServer",
            pid_file=self.fx_pid_file,
            expected_name="FXServer.exe",
            expected_path=self.fxserver_exe,
        )

    def discord_bot_status(self) -> ComponentStatus:
        return self._managed_process_status(
            name="Discord Bot",
            pid_file=self.bot_pid_file,
            expected_name="python.exe",
            expected_path=self.bot_python,
            command_contains=str(self.bot_file),
        )

    def server_status(self) -> ComponentStatus:
        state = self._bot_last_known_online()
        if state is True:
            return ComponentStatus("Server", "Online", "Observed by Discord bot")
        if state is False:
            return ComponentStatus("Server", "Offline", "Observed by Discord bot")
        return ComponentStatus("Server", "Unknown", "Waiting for Discord bot observation")

    def txadmin_status(self) -> ComponentStatus:
        if self._tcp_port_open(self.txadmin_host, self.txadmin_port):
            return ComponentStatus("txAdmin", "Running", self.config.txadmin_url)
        return ComponentStatus("txAdmin", "Stopped", f"Not listening on {self.txadmin_host}:{self.txadmin_port}")

    def database_status(self) -> ComponentStatus:
        endpoint = self._database_endpoint()
        if endpoint is None:
            return ComponentStatus("Database", "Unknown", "No database endpoint found")

        host, port = endpoint
        if self._tcp_port_open(host, port):
            return ComponentStatus("Database", "Running", f"Listening on {host}:{port}")
        return ComponentStatus("Database", "Stopped", f"Not listening on {host}:{port}")

    def fxserver_is_running(self) -> bool:
        return self.fxserver_status().state == "Running"

    def server_is_offline(self) -> bool:
        return self._bot_last_known_online() is False

    def txadmin_is_running(self) -> bool:
        return self.txadmin_status().state == "Running"

    def _bot_last_known_online(self) -> bool | None:
        state_path = self.bot_dir / "bot_state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        value = state.get("last_known_online")
        if isinstance(value, bool):
            return value
        return None

    def _managed_process_status(
        self,
        name: str,
        pid_file: Path,
        expected_name: str,
        expected_path: Path | None = None,
        command_contains: str | None = None,
    ) -> ComponentStatus:
        pid = self._read_pid(pid_file)
        if pid is not None:
            process = self._get_process(pid)
            if process and self._matches_process(process, expected_name, expected_path, command_contains):
                return ComponentStatus(name, "Running", f"PID {pid}")

            self._remove_stale_pid(pid_file)
            return ComponentStatus(name, "Stopped", "Stale PID file removed")

        for process in self._get_processes_by_name(expected_name):
            if self._matches_process(process, expected_name, expected_path, command_contains):
                return ComponentStatus(name, "Running", f"Untracked PID {process['ProcessId']}")

        return ComponentStatus(name, "Stopped", "No PID file")

    def _matches_process(
        self,
        process: dict[str, Any],
        expected_name: str,
        expected_path: Path | None,
        command_contains: str | None,
    ) -> bool:
        if str(process.get("Name", "")).lower() != expected_name.lower():
            return False

        if expected_path is not None:
            executable = process.get("ExecutablePath")
            if not executable:
                return False
            if self._normalized_path(executable).lower() != self._normalized_path(expected_path).lower():
                return False

        if command_contains:
            command_line = str(process.get("CommandLine") or "").lower()
            if command_contains.lower() not in command_line:
                return False

        return True

    def _get_process(self, pid: int) -> dict[str, Any] | None:
        output = self._powershell_json(
            "$process = Get-CimInstance Win32_Process -Filter \"ProcessId = %d\" -ErrorAction SilentlyContinue; "
            "if ($process) { $process | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress }"
            % pid
        )
        if isinstance(output, dict):
            return output
        return None

    def _get_processes_by_name(self, name: str) -> list[dict[str, Any]]:
        safe_name = name.replace("'", "''")
        output = self._powershell_json(
            "Get-CimInstance Win32_Process -Filter \"Name = '%s'\" -ErrorAction SilentlyContinue | "
            "Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress" % safe_name
        )
        if isinstance(output, list):
            return [item for item in output if isinstance(item, dict)]
        if isinstance(output, dict):
            return [output]
        return []

    def _powershell_json(self, command: str) -> Any:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=8,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return None

        text = result.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _read_pid(self, path: Path) -> int | None:
        try:
            return int(path.read_text(encoding="utf-8").strip().splitlines()[0])
        except (OSError, ValueError, IndexError):
            return None

    def _remove_stale_pid(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def _database_endpoint(self) -> tuple[str, int] | None:
        try:
            cfg = self.server_cfg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None

        match = re.search(r'mysql_connection_string\s+"([^"]+)"', cfg)
        if not match:
            return None

        parsed = urlparse(match.group(1))
        if not parsed.hostname:
            return None
        return parsed.hostname, parsed.port or 3306

    def _tcp_port_open(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            return False

    def _normalized_path(self, path: str | Path) -> str:
        return str(Path(path).resolve())
