from __future__ import annotations

import ctypes
import errno
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from app.updater.exceptions import UpdateLaunchError, UpdateProcessTimeoutError

class ApplicationLauncher:
    """Interface for waiting on and launching ScenarioRP Manager."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("ScenarioRPUpdater")

    def wait_for_exit(self, app_dir: Path, timeout_seconds: float, manager_pid: int | None = None) -> None:
        """Wait until the currently running manager process exits."""
        if manager_pid is None:
            self.logger.info("No manager PID supplied; continuing without process wait")
            return
        deadline = time.monotonic() + timeout_seconds
        while self.process_exists(manager_pid):
            if time.monotonic() >= deadline:
                raise UpdateProcessTimeoutError(f"Timed out waiting for manager PID {manager_pid} to exit.")
            time.sleep(0.25)

    def launch(self, app_dir: Path) -> None:
        """Launch ScenarioRP Manager after a successful update."""
        executable = app_dir / "ScenarioRP-Manager.exe"
        if not executable.is_file():
            raise UpdateLaunchError(f"Cannot launch missing executable: {executable}")
        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(
                [str(executable)],
                cwd=str(app_dir),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creationflags,
            )
            self.logger.info("Launched updated application: %s", executable)
        except OSError as exc:
            raise UpdateLaunchError(f"Could not launch updated application: {executable}") from exc

    def process_exists(self, pid: int) -> bool:
        """Return True if a process exists for pid."""
        if pid <= 0:
            return False
        if os.name == "nt":
            return self._windows_process_exists(pid)
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError as exc:
            return exc.errno != errno.ESRCH

    def _windows_process_exists(self, pid: int) -> bool:
        if pid == os.getpid():
            return True
        try:
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        except (AttributeError, OSError):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                return getattr(exc, "winerror", None) == 5
            return True
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        try:
            return ctypes.get_last_error() == 5
        except AttributeError:
            return False
