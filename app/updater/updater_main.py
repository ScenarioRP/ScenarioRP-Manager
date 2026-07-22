from __future__ import annotations

import argparse
from pathlib import Path

from app.updater.installer import UpdateInstaller
from app.updater.models import InstallerConfig


def parse_args(argv: list[str] | None = None) -> InstallerConfig:
    """Parse command-line arguments for the future standalone updater executable."""
    parser = argparse.ArgumentParser(description="Install a downloaded ScenarioRP Manager update.")
    parser.add_argument("--app", required=True, help="ScenarioRP Manager application directory.")
    parser.add_argument("--zip", required=True, help="Downloaded update ZIP file.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Seconds to wait for the manager to exit.")
    args = parser.parse_args(argv)
    return InstallerConfig(app_dir=Path(args.app), zip_path=Path(args.zip), timeout_seconds=args.timeout)


def main(argv: list[str] | None = None) -> int:
    """Create the installer and start the future installer flow."""
    config = parse_args(argv)
    installer = UpdateInstaller(config)
    installer.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
