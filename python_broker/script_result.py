from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptResult:
    """Result returned by the broker after a PowerShell script completes."""

    script_name: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    command: tuple[str, ...]
    duration_seconds: float

    @property
    def status_lines(self) -> tuple[str, ...]:
        """Return structured STATUS lines from stdout without interpreting their state."""

        return tuple(line for line in self.stdout.splitlines() if line.startswith("STATUS|"))
