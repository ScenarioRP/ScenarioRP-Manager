from __future__ import annotations

import argparse
from pathlib import Path

from app.updater.exceptions import (
    UpdateBackupError,
    UpdateError,
    UpdateExtractionError,
    UpdateInstallerArgumentError,
    UpdateLaunchError,
    UpdatePackageValidationError,
    UpdateProcessTimeoutError,
    UpdateReplacementError,
    UpdateRollbackError,
    UpdateZipValidationError,
)
from app.updater.installer import UpdateInstaller
from app.updater.installer.logging_config import close_installer_logging, configure_installer_logging
from app.updater.models import InstallerConfig

EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_INVALID_ARGUMENTS = 2
EXIT_PROCESS_TIMEOUT = 3
EXIT_INVALID_PACKAGE = 4
EXIT_BACKUP_FAILURE = 5
EXIT_REPLACEMENT_FAILURE = 6
EXIT_ROLLBACK_FAILURE = 7
EXIT_LAUNCH_FAILURE = 8


def parse_args(argv: list[str] | None = None) -> InstallerConfig:
    """Parse command-line arguments for the future standalone updater executable."""
    parser = argparse.ArgumentParser(description="Install a downloaded ScenarioRP Manager update.")
    parser.add_argument("--app", required=True, help="ScenarioRP Manager application directory.")
    parser.add_argument("--zip", required=True, help="Downloaded update ZIP file.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Seconds to wait for the manager to exit.")
    parser.add_argument("--pid", type=int, default=None, help="Optional ScenarioRP Manager process ID to wait for.")
    args = parser.parse_args(argv)
    return InstallerConfig(
        app_dir=Path(args.app),
        zip_path=Path(args.zip),
        timeout_seconds=args.timeout,
        manager_pid=args.pid,
    )


def main(argv: list[str] | None = None) -> int:
    """Create the installer and start the future installer flow."""
    try:
        config = parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_INVALID_ARGUMENTS

    logger = configure_installer_logging(config.log_path)
    try:
        installer = UpdateInstaller(config, logger=logger)
        installer.run()
        return EXIT_SUCCESS
    except UpdateError as exc:
        logger.exception("Updater failed: %s", exc)
        return _exit_code_for_error(exc)
    except Exception as exc:
        logger.exception("Unexpected updater failure: %s", exc)
        return EXIT_GENERAL_FAILURE
    finally:
        close_installer_logging(logger)


def _exit_code_for_error(exc: UpdateError) -> int:
    if isinstance(exc, UpdateInstallerArgumentError):
        return EXIT_INVALID_ARGUMENTS
    if isinstance(exc, UpdateProcessTimeoutError):
        return EXIT_PROCESS_TIMEOUT
    if isinstance(exc, (UpdateZipValidationError, UpdateExtractionError, UpdatePackageValidationError)):
        return EXIT_INVALID_PACKAGE
    if isinstance(exc, UpdateBackupError):
        return EXIT_BACKUP_FAILURE
    if isinstance(exc, UpdateReplacementError):
        return EXIT_REPLACEMENT_FAILURE
    if isinstance(exc, UpdateRollbackError):
        return EXIT_ROLLBACK_FAILURE
    if isinstance(exc, UpdateLaunchError):
        return EXIT_LAUNCH_FAILURE
    return EXIT_GENERAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
