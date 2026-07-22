from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import sys
from zipfile import ZipInfo

PROTECTED_TOP_LEVEL_NAMES = {"user_data", "ScenarioRPUpdater.exe"}


def is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path resolves inside parent."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def ensure_inside(path: Path, parent: Path) -> Path:
    """Resolve path and raise ValueError if it escapes parent."""
    resolved = path.resolve()
    if not is_relative_to(resolved, parent.resolve()):
        raise ValueError(f"Path escapes expected directory: {path}")
    return resolved


def top_level_name(path: Path, root: Path) -> str:
    """Return the top-level name of path relative to root."""
    relative = path.resolve().relative_to(root.resolve())
    return relative.parts[0] if relative.parts else ""


def running_updater_paths(app_dir: Path) -> set[Path]:
    """Return protected runtime updater paths that are inside app_dir."""
    candidates = {Path(sys.executable)}
    argv0 = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
    if argv0 is not None:
        candidates.add(argv0)
    protected: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if is_relative_to(resolved, app_dir.resolve()):
            protected.add(resolved)
    return protected


def is_protected_path(path: Path, app_dir: Path) -> bool:
    """Return True for files/directories the installer must not modify."""
    resolved_app = app_dir.resolve()
    resolved = path.resolve()
    try:
        top_name = top_level_name(resolved, resolved_app)
    except ValueError:
        return True
    if top_name in PROTECTED_TOP_LEVEL_NAMES:
        return True
    return any(resolved == protected or protected in resolved.parents for protected in running_updater_paths(app_dir))


def iter_application_managed_paths(app_dir: Path) -> list[Path]:
    """Return top-level install paths managed by the application, excluding protected paths."""
    return [path for path in app_dir.iterdir() if not is_protected_path(path, app_dir)]


def remove_path(path: Path, app_dir: Path) -> None:
    """Remove a file or directory after confirming it is safe to modify."""
    ensure_inside(path, app_dir)
    if is_protected_path(path, app_dir):
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onerror=_handle_remove_readonly)
    else:
        _make_writable(path)
        path.unlink()


def copy_path(source: Path, destination: Path, app_dir: Path | None = None) -> None:
    """Copy source to destination without following directory symlinks."""
    if app_dir is not None:
        ensure_inside(destination, app_dir)
        if is_protected_path(destination, app_dir):
            return
    if source.is_dir() and not source.is_symlink():
        shutil.copytree(source, destination, symlinks=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)


def archive_member_is_symlink(member: ZipInfo) -> bool:
    """Return True when a ZIP member is a Unix symlink entry."""
    mode = member.external_attr >> 16
    return stat.S_ISLNK(mode)


def archive_member_is_regular_or_directory(member: ZipInfo) -> bool:
    """Return True when a ZIP member is a regular file or directory."""
    if member.is_dir():
        return True
    mode = member.external_attr >> 16
    if mode == 0:
        return True
    if stat.S_IFMT(mode) == 0:
        return True
    return stat.S_ISREG(mode)


def safe_archive_target(extract_root: Path, member_name: str) -> Path:
    """Return the safe extraction target for member_name or raise ValueError."""
    normalized = member_name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or Path(normalized).is_absolute():
        raise ValueError(f"Unsafe archive path: {member_name}")
    parts = Path(normalized).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe archive path: {member_name}")
    if len(parts) > 0 and os.path.splitdrive(parts[0])[0]:
        raise ValueError(f"Unsafe archive path: {member_name}")
    target = extract_root / Path(*parts)
    return ensure_inside(target, extract_root)


def _make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError:
        return


def _handle_remove_readonly(function: object, path: str, exc_info: object) -> None:
    target = Path(path)
    _make_writable(target)
    function(path)
