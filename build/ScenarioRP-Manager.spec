# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


REPO_ROOT = Path(SPECPATH).resolve().parent
ICON_CANDIDATES = [
    REPO_ROOT / "assets" / "ScenarioRP-Manager.ico",
    REPO_ROOT / "assets" / "app.ico",
]
ICON_PATH = next((path for path in ICON_CANDIDATES if path.is_file()), None)

datas = [
    (str(REPO_ROOT / "app" / "ui" / "main_window.ui"), "app/ui"),
    (str(REPO_ROOT / "app" / "ui" / "styles.qss"), "app/ui"),
]
datas.extend((str(path), "app/scripts") for path in (REPO_ROOT / "app" / "scripts").glob("*.ps1"))

hiddenimports = [
    "PySide6.QtUiTools",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
]

a = Analysis(
    [str(REPO_ROOT / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScenarioRP-Manager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ScenarioRP-Manager",
    contents_directory="_internal",
)
