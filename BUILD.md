# Windows portable build

This project builds a portable Windows folder containing the ScenarioRP Manager GUI executable and the standalone update installer executable.

End users do not need Python, a virtual environment, a terminal, pip, or source files.

## Prerequisites

- Windows
- Python matching the project development environment
- Runtime dependencies installed from `requirements.txt`
- Build dependencies installed from `requirements-build.txt`

Install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
```

## Build command

From the repository root:

```powershell
python scripts/build_windows.py
```

The script builds:

- `ScenarioRP-Manager.exe` from `main.py`
- `ScenarioRPUpdater.exe` from `app/updater/updater_main.py`

Both are built with PyInstaller one-folder mode. The final portable folder is assembled at:

```text
dist/ScenarioRP-Manager/
```

The portable ZIP is created at:

```text
dist/ScenarioRP-Manager-v0.1.1-Windows.zip
```

The version is read from `app/updater/client/version.py`; do not duplicate it manually in the build script.

## Output layout

```text
dist/
└── ScenarioRP-Manager/
    ├── ScenarioRP-Manager.exe
    ├── ScenarioRPUpdater.exe
    ├── _internal/
    ├── assets/
    │   └── myLogo.png
    ├── system_data/
    │   ├── config.json
    │   └── update_config.json
    └── user_data/
        ├── cache/
        ├── logs/
        ├── saves/
        ├── state/
        └── updates/
            ├── backups/
            ├── downloads/
            └── extracted/
```

## Path behavior

In source mode, `AppPaths` resolves the application root from the repository checkout.

In PyInstaller frozen mode, `AppPaths` resolves:

- application root from the executable directory
- Python/data bundle files from `_internal`
- writable data from `user_data` beside the executable
- `assets` and `system_data` beside the executable

This means writable update data is never stored inside `_internal`.

## Validation performed by the build script

The build script verifies:

- both executables exist
- `_internal` exists
- `assets/myLogo.png` exists
- `system_data/config.json` exists
- `system_data/update_config.json` exists
- `user_data` exists
- no `.venv`, `tests`, `__pycache__`, `.git`, or `.github` directories are bundled
- `user_data` contains no personal files, logs, downloaded update ZIPs, or backups

## Manual smoke test

After building:

1. Open `dist/ScenarioRP-Manager/ScenarioRP-Manager.exe`.
2. Confirm the window initializes and remains open.
3. Close the application normally.
4. Run updater help:

   ```powershell
   dist\ScenarioRP-Manager\ScenarioRPUpdater.exe --help
   ```

   For a visible console updater build, use:

   ```powershell
   python scripts/build_windows.py --updater-console
   ```

5. Do not run a real update against the development checkout. Use a temporary fake installation when testing updater replacement behavior.

If GUI automation is unreliable on the build machine, the first three steps must be verified manually.

## Sending to another person

1. Send `dist/ScenarioRP-Manager-v0.1.1-Windows.zip`.
2. The user extracts the entire ZIP.
3. The user opens `ScenarioRP-Manager.exe`.

Do not run the application directly from inside the ZIP.

## Cleaning build output

The normal build command removes stale generated output from:

```text
build/work/
dist/ScenarioRP-Manager/
dist/ScenarioRP-Manager-v0.1.1-Windows.zip
```

You can also delete `build/work/` and `dist/` manually.

## Current limitations

- No GitHub Actions build is configured yet.
- No installer wizard or MSI is created.
- The manager does not yet launch the updater automatically.
- Old backups are not automatically deleted.
