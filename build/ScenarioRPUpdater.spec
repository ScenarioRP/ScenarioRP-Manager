# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path


REPO_ROOT = Path(SPECPATH).resolve().parent
UPDATER_CONSOLE = os.environ.get("SCENARIORP_UPDATER_CONSOLE") == "1"

a = Analysis(
    [str(REPO_ROOT / "app" / "updater" / "updater_main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScenarioRPUpdater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=UPDATER_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ScenarioRPUpdater",
    contents_directory="_internal",
)
