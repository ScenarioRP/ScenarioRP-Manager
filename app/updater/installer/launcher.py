from __future__ import annotations

from pathlib import Path


class ApplicationLauncher:
    """Interface for waiting on and launching ScenarioRP Manager."""

    def wait_for_exit(self, app_dir: Path, timeout_seconds: float) -> None:
        """Wait until the currently running manager process exits."""
        raise NotImplementedError("Process waiting is not implemented yet.")

    def launch(self, app_dir: Path) -> None:
        """Launch ScenarioRP Manager after a successful update."""
        raise NotImplementedError("Application launching is not implemented yet.")
