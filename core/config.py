from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    fxserver_exe: str
    txdata_dir: str
    server_cfg: str
    discord_bot_dir: str
    discord_bot_python: str
    discord_bot_file: str
    txadmin_profile: str
    txadmin_url: str
    logs_dir: str
    backups_dir: str


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return AppConfig(**raw)
