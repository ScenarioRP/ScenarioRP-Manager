# ScenarioRP Manager

Local PySide6 control center for the ScenarioRP development environment.

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

## Responsibility Boundary

ScenarioRP Manager launches and monitors the server environment, embeds txAdmin, manages ScenarioRP helper components, and can close the remaining server shell and Discord bot after the server is offline.

txAdmin is the source of truth for FiveM server administration. Stop, restart, console, players, resources, recipes, settings, and runtime monitoring are handled through txAdmin.

## Script Backend

The GUI calls only lifecycle scripts:

- `start-all.ps1`
- `close-server-shell.ps1`

Supporting scripts are also executable directly:

- `start-server.ps1`
- `start-discord-bot.ps1`
- `stop-discord-bot.ps1`
- `restart-discord-bot.ps1`

`close-server-shell.ps1` backs the Close Shell action. It does not announce Discord Offline and must only run after the Server-Status bot has observed the server offline. It closes the remaining FXServer shell and then stops the Server-Status bot. txAdmin remains responsible for stopping the FiveM server itself.

## UI Editing

The main window layout lives in `ui/main_window.ui` and can be edited with Qt Designer. Keep the existing object names when changing widgets, because `ui/main_window.py` connects logic by those names.
