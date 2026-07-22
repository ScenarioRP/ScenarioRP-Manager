from __future__ import annotations

from pathlib import Path


class RollbackManager:
    """Interface for restoring the previous application version."""

    def rollback(self, app_dir: Path) -> None:
        """Restore the application from the latest backup."""
        raise NotImplementedError("Rollback is not implemented yet.")
