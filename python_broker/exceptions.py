from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from python_broker.script_result import ScriptResult


class BrokerError(Exception):
    """Base exception for broker-layer failures."""


class InvalidScriptNameError(BrokerError):
    """Raised when a requested script path is unsafe or invalid."""

    def __init__(self, script_name: str) -> None:
        super().__init__(f"Invalid PowerShell script name: {script_name!r}")
        self.script_name = script_name


class ScriptNotFoundError(BrokerError):
    """Raised when a requested PowerShell script does not exist."""

    def __init__(self, script_name: str, script_path: Path) -> None:
        super().__init__(f"PowerShell script not found: {script_name!r} ({script_path})")
        self.script_name = script_name
        self.script_path = script_path


class PowerShellNotFoundError(BrokerError):
    """Raised when the configured PowerShell executable cannot be started."""

    def __init__(self, executable: str) -> None:
        super().__init__(f"PowerShell executable not found: {executable!r}")
        self.executable = executable


class ScriptTimeoutError(BrokerError):
    """Raised when a PowerShell script exceeds the configured timeout."""

    def __init__(self, script_name: str, timeout_seconds: float, stdout: str = "", stderr: str = "") -> None:
        super().__init__(f"PowerShell script timed out after {timeout_seconds:.1f}s: {script_name!r}")
        self.script_name = script_name
        self.timeout_seconds = timeout_seconds
        self.stdout = stdout
        self.stderr = stderr


class ScriptExecutionError(BrokerError):
    """Raised when a PowerShell script exits with a non-zero exit code."""

    def __init__(self, result: "ScriptResult") -> None:
        super().__init__(f"PowerShell script failed with exit code {result.exit_code}: {result.script_name!r}")
        self.result = result


class InvalidScriptOutputError(BrokerError):
    """Raised when a script does not return the expected broker-compatible output."""

    def __init__(self, script_name: str, message: str, stdout: str = "", stderr: str = "") -> None:
        super().__init__(f"Invalid output from {script_name!r}: {message}")
        self.script_name = script_name
        self.stdout = stdout
        self.stderr = stderr
