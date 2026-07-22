from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import uuid

from app.updater.exceptions import UpdateBackupError
from app.updater.installer.filesystem import copy_path, iter_application_managed_paths
from app.updater.models import BackupInfo

class BackupManager:
    """Interface for backing up current application files."""

    def create_backup(self, app_dir: Path, backups_dir: Path) -> BackupInfo:
        """Create a backup for app_dir and return the backup directory."""
        created_at = datetime.now()
        backup_dir = self._unique_backup_dir(backups_dir, created_at)
        backed_up_paths: list[str] = []
        try:
            backup_dir.mkdir(parents=True, exist_ok=False)
            for source in iter_application_managed_paths(app_dir):
                relative = source.relative_to(app_dir)
                copy_path(source, backup_dir / relative)
                backed_up_paths.append(relative.as_posix())
            manifest_path = backup_dir / "backup_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "created_at": created_at.isoformat(timespec="seconds"),
                        "app_dir": str(app_dir.resolve()),
                        "backed_up_paths": backed_up_paths,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            return BackupInfo(
                backup_dir=backup_dir,
                manifest_path=manifest_path,
                app_dir=app_dir,
                created_at=created_at,
                backed_up_paths=tuple(backed_up_paths),
            )
        except OSError as exc:
            raise UpdateBackupError(f"Could not create backup in {backup_dir}") from exc

    def _unique_backup_dir(self, backups_dir: Path, created_at: datetime) -> Path:
        timestamp = created_at.strftime("%Y-%m-%d_%H-%M-%S")
        candidate = backups_dir / timestamp
        if not candidate.exists():
            return candidate
        return backups_dir / f"{timestamp}_{uuid.uuid4().hex[:8]}"
