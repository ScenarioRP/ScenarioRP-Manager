from __future__ import annotations

import logging
from pathlib import Path


def configure_installer_logging(log_path: Path) -> logging.Logger:
    """Configure updater logging, falling back safely when file logging fails."""
    logger = logging.getLogger("ScenarioRPUpdater")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    close_installer_logging(logger)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError:
        handler = logging.NullHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def close_installer_logging(logger: logging.Logger) -> None:
    """Close and remove installer log handlers."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
