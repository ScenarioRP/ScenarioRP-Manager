# ScenarioRP Manager

Local PySide6 manager for the ScenarioRP development server.

## Setup

```powershell
cd ScenarioRP-Manager
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\manager.ps1
```

## Configuration

Edit `config.json` when a relative path changes. Relative paths are resolved from the ScenarioRP project root, so the project can move between drive letters.

## MVP Limits

The current MVP is a PySide6 frontend that runs PowerShell scripts from `scripts/` and displays their output.

Server operations live in standalone PowerShell scripts. Each script can be run manually from PowerShell.

## UI Editing

The main window layout lives in `ui/main_window.ui` and can be edited with Qt Designer. Keep the existing object names when changing widgets, because `ui/main_window.py` connects logic by those names.
