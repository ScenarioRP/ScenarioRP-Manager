from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / "build"
BUILD_WORK_DIR = BUILD_DIR / "work"
PYINSTALLER_DIST_DIR = BUILD_WORK_DIR / "pyinstaller"
DIST_DIR = PROJECT_ROOT / "dist"
FINAL_DIST_DIR = DIST_DIR / "ScenarioRP-Manager"
MANAGER_SPEC = BUILD_DIR / "ScenarioRP-Manager.spec"
UPDATER_SPEC = BUILD_DIR / "ScenarioRPUpdater.spec"

REQUIRED_DISTRIBUTION_FILES = (
    Path("ScenarioRP-Manager.exe"),
    Path("ScenarioRPUpdater.exe"),
    Path("_internal"),
    Path("assets") / "myLogo.png",
    Path("system_data") / "config.json",
    Path("system_data") / "update_config.json",
    Path("user_data"),
)
REQUIRED_USER_DATA_DIRS = (
    Path("logs"),
    Path("cache"),
    Path("saves"),
    Path("state"),
    Path("updates"),
    Path("updates") / "downloads",
    Path("updates") / "extracted",
    Path("updates") / "backups",
)
FORBIDDEN_BUNDLED_NAMES = {".git", ".github", ".venv", "tests", "__pycache__"}


class BuildError(RuntimeError):
    """Raised when the Windows distribution build cannot be completed safely."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ScenarioRP Manager portable Windows distribution.")
    parser.add_argument("--skip-zip", action="store_true", help="Build the folder without creating a portable ZIP.")
    parser.add_argument("--no-clean", action="store_true", help="Keep existing build output before building.")
    parser.add_argument(
        "--updater-console",
        action="store_true",
        help="Build ScenarioRPUpdater.exe with a console window for manual troubleshooting.",
    )
    args = parser.parse_args(argv)

    try:
        build_distribution(
            create_zip=not args.skip_zip,
            clean=not args.no_clean,
            updater_console=args.updater_console,
        )
        return 0
    except BuildError as exc:
        raise SystemExit(str(exc)) from exc


def build_distribution(*, create_zip: bool = True, clean: bool = True, updater_console: bool = False) -> Path:
    """Build and validate the portable Windows distribution folder."""
    ensure_windows()
    if clean:
        clean_outputs()

    run_pyinstaller(MANAGER_SPEC)
    run_pyinstaller(UPDATER_SPEC, updater_console=updater_console)
    assemble_distribution()
    validate_distribution(FINAL_DIST_DIR)

    if create_zip:
        return create_zip_archive(FINAL_DIST_DIR, read_app_version())
    return FINAL_DIST_DIR


def ensure_windows() -> None:
    """Reject non-Windows hosts because the output executable target is Windows."""
    if os.name != "nt":
        raise BuildError("Windows builds must be created on Windows.")


def clean_outputs() -> None:
    """Remove only known generated build outputs."""
    safe_rmtree(BUILD_WORK_DIR, BUILD_DIR)
    safe_rmtree(FINAL_DIST_DIR, DIST_DIR)
    version = read_app_version()
    zip_path = DIST_DIR / f"ScenarioRP-Manager-v{version}-Windows.zip"
    if zip_path.exists():
        ensure_inside(zip_path, DIST_DIR)
        zip_path.unlink()


def run_pyinstaller(spec_path: Path, *, updater_console: bool = False) -> None:
    """Run PyInstaller for one maintained spec file."""
    if not spec_path.is_file():
        raise BuildError(f"Missing PyInstaller spec file: {spec_path}")

    env = os.environ.copy()
    if updater_console:
        env["SCENARIORP_UPDATER_CONSOLE"] = "1"

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--noconfirm",
        "--clean",
        "--workpath",
        str(BUILD_WORK_DIR / spec_path.stem),
        "--distpath",
        str(PYINSTALLER_DIST_DIR),
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=False)
    if completed.returncode != 0:
        raise BuildError(f"PyInstaller failed for {spec_path.name} with exit code {completed.returncode}.")


def assemble_distribution() -> None:
    """Assemble the final shared portable distribution folder."""
    manager_bundle = PYINSTALLER_DIST_DIR / "ScenarioRP-Manager"
    updater_bundle = PYINSTALLER_DIST_DIR / "ScenarioRPUpdater"
    if not manager_bundle.is_dir():
        raise BuildError(f"Missing manager PyInstaller output: {manager_bundle}")
    if not updater_bundle.is_dir():
        raise BuildError(f"Missing updater PyInstaller output: {updater_bundle}")

    safe_rmtree(FINAL_DIST_DIR, DIST_DIR)
    FINAL_DIST_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(manager_bundle, FINAL_DIST_DIR)

    merge_tree(updater_bundle / "_internal", FINAL_DIST_DIR / "_internal")
    copy_required_file(updater_bundle / "ScenarioRPUpdater.exe", FINAL_DIST_DIR / "ScenarioRPUpdater.exe")

    copy_clean_tree(PROJECT_ROOT / "assets", FINAL_DIST_DIR / "assets")
    copy_clean_tree(PROJECT_ROOT / "system_data", FINAL_DIST_DIR / "system_data")
    create_clean_user_data(FINAL_DIST_DIR / "user_data")


def copy_required_file(source: Path, destination: Path) -> None:
    """Copy a required generated file."""
    if not source.is_file():
        raise BuildError(f"Missing required generated file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_clean_tree(source: Path, destination: Path) -> None:
    """Copy a source data directory without Python cache files."""
    if not source.is_dir():
        raise BuildError(f"Missing required data directory: {source}")
    if destination.exists():
        safe_rmtree(destination, FINAL_DIST_DIR)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))


def merge_tree(source: Path, destination: Path) -> None:
    """Merge one PyInstaller internal folder into the shared internal folder."""
    if not source.is_dir():
        raise BuildError(f"Missing updater internal bundle: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def create_clean_user_data(user_data_dir: Path) -> None:
    """Create an empty writable user_data layout for the portable package."""
    if user_data_dir.exists():
        safe_rmtree(user_data_dir, FINAL_DIST_DIR)
    for relative in REQUIRED_USER_DATA_DIRS:
        (user_data_dir / relative).mkdir(parents=True, exist_ok=True)


def validate_distribution(distribution_dir: Path) -> None:
    """Validate that the portable distribution contains only expected runtime output."""
    if not distribution_dir.is_dir():
        raise BuildError(f"Distribution folder does not exist: {distribution_dir}")

    for relative in REQUIRED_DISTRIBUTION_FILES:
        path = distribution_dir / relative
        if not path.exists():
            raise BuildError(f"Missing distribution item: {relative}")

    for path in distribution_dir.rglob("*"):
        if path.name in FORBIDDEN_BUNDLED_NAMES:
            raise BuildError(f"Forbidden development item bundled: {path.relative_to(distribution_dir)}")

    validate_clean_user_data(distribution_dir / "user_data")


def validate_clean_user_data(user_data_dir: Path) -> None:
    """Ensure user_data contains only clean empty runtime directories."""
    if not user_data_dir.is_dir():
        raise BuildError("Missing user_data directory.")

    for relative in REQUIRED_USER_DATA_DIRS:
        path = user_data_dir / relative
        if not path.is_dir():
            raise BuildError(f"Missing clean user_data directory: {relative}")

    for path in user_data_dir.rglob("*"):
        if path.is_file():
            raise BuildError(f"user_data contains a generated or personal file: {path.relative_to(user_data_dir)}")


def create_zip_archive(distribution_dir: Path, version: str) -> Path:
    """Create the portable Windows ZIP with one wrapper folder."""
    zip_path = DIST_DIR / f"ScenarioRP-Manager-v{version}-Windows.zip"
    if zip_path.exists():
        ensure_inside(zip_path, DIST_DIR)
        zip_path.unlink()

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(distribution_dir.rglob("*")):
            archive.write(path, path.relative_to(DIST_DIR))
    return zip_path


def read_app_version() -> str:
    """Read APP_VERSION from the update client without importing application code."""
    version_file = PROJECT_ROOT / "app" / "updater" / "client" / "version.py"
    module = ast.parse(version_file.read_text(encoding="utf-8"), filename=str(version_file))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise BuildError(f"Could not read APP_VERSION from {version_file}")


def safe_rmtree(path: Path, allowed_parent: Path) -> None:
    """Remove a generated directory only when it is inside the expected parent."""
    if not path.exists():
        return
    ensure_inside(path, allowed_parent)
    if path.resolve() == allowed_parent.resolve():
        raise BuildError(f"Refusing to remove parent directory directly: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def ensure_inside(path: Path, parent: Path) -> Path:
    """Resolve path and verify it remains inside parent."""
    resolved = path.resolve()
    parent_resolved = parent.resolve()
    try:
        resolved.relative_to(parent_resolved)
    except ValueError as exc:
        raise BuildError(f"Path escapes expected directory: {path}") from exc
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
