from __future__ import annotations

from pathlib import Path
import subprocess
from time import monotonic
from typing import Iterable

from python_broker.exceptions import (
    InvalidScriptNameError,
    InvalidScriptOutputError,
    PowerShellNotFoundError,
    ScriptExecutionError,
    ScriptNotFoundError,
    ScriptTimeoutError,
)
from python_broker.script_result import ScriptResult


DEFAULT_TIMEOUT_SECONDS = 120.0
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class PowerShellRunner:
    """Broker API for executing ScenarioRP PowerShell scripts.

    The GUI should call this class instead of constructing PowerShell commands,
    resolving script paths, or handling process failures directly.
    """

    def __init__(
        self,
        scripts_dir: Path | str | None = None,
        *,
        powershell_executable: str = "powershell",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        working_dir: Path | str | None = None,
    ) -> None:
        """Create a PowerShell broker.

        Args:
            scripts_dir: Directory containing ScenarioRP `.ps1` scripts. Defaults
                to `<manager_dir>/scripts`.
            powershell_executable: Executable used to run scripts. Defaults to
                Windows PowerShell (`powershell`).
            timeout_seconds: Default execution timeout for public methods.
            working_dir: Process working directory. Defaults to the manager
                directory, preserving the current GUI/script contract.

        Raises:
            No exception is raised during construction; script availability and
            PowerShell availability are checked when a script is executed.
        """

        self.manager_dir = Path(__file__).resolve().parents[1]
        self.project_root = self.manager_dir.parent
        self.scripts_dir = Path(scripts_dir).resolve() if scripts_dir is not None else self.manager_dir / "scripts"
        self.powershell_executable = powershell_executable
        self.timeout_seconds = timeout_seconds
        self.working_dir = Path(working_dir).resolve() if working_dir is not None else self.manager_dir

    def run_script(
        self,
        script_name: str,
        args: Iterable[str | int | float | Path] | None = None,
        *,
        timeout_seconds: float | None = None,
        check: bool = True,
    ) -> ScriptResult:
        """Execute a PowerShell script and return its captured result.

        Args:
            script_name: Script file name or safe relative path under
                `scripts_dir`.
            args: Command-line arguments passed to the script unchanged after
                string conversion.
            timeout_seconds: Optional timeout override for this call.
            check: When true, non-zero exit codes raise `ScriptExecutionError`.

        Returns:
            `ScriptResult` containing stdout, stderr, exit code, command, and
            duration.

        Raises:
            InvalidScriptNameError: The script name is unsafe or not a `.ps1`.
            ScriptNotFoundError: The script does not exist under `scripts_dir`.
            PowerShellNotFoundError: The PowerShell executable cannot be found.
            ScriptTimeoutError: The script exceeds the timeout.
            ScriptExecutionError: The script exits non-zero and `check` is true.
        """

        script_path = self._script_path(script_name)
        script_args = tuple(str(arg) for arg in (args or ()))
        command = (
            self.powershell_executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *script_args,
        )

        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        started_at = monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.working_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
        except FileNotFoundError as exc:
            raise PowerShellNotFoundError(self.powershell_executable) from exc
        except subprocess.TimeoutExpired as exc:
            stdout = self._decode_timeout_output(exc.stdout)
            stderr = self._decode_timeout_output(exc.stderr)
            raise ScriptTimeoutError(script_name, timeout, stdout=stdout, stderr=stderr) from exc

        result = ScriptResult(
            script_name=script_name,
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            command=command,
            duration_seconds=monotonic() - started_at,
        )

        if check and not result.success:
            raise ScriptExecutionError(result)

        return result

    def start_server(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Start the FXServer/txAdmin process using `start-server.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("start-server.ps1", timeout_seconds=timeout_seconds, check=check)

    def stop_server(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Run the existing server-shell shutdown flow.

        The current repository does not contain `stop-server.ps1`; its public
        shutdown entry point is `close-server-shell.ps1`.

        Returns:
            `ScriptResult` from `close-server-shell.ps1`.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.close_server_shell(timeout_seconds=timeout_seconds, check=check)

    def restart_server(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Restart the server using `restart-server.ps1` when that script exists.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            ScriptNotFoundError: The current repository has no restart server
                script.
            Broker exceptions from `run_script`.
        """

        return self.run_script("restart-server.ps1", timeout_seconds=timeout_seconds, check=check)

    def get_status(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Collect script-based status using `status.ps1`.

        Returns:
            `ScriptResult` with at least one `STATUS|...` line in stdout.

        Raises:
            ScriptNotFoundError: The current repository has no status script.
            InvalidScriptOutputError: The script succeeds but returns no
                structured `STATUS|...` line.
            Broker exceptions from `run_script`.
        """

        return self._run_status_script("status.ps1", timeout_seconds=timeout_seconds, check=check)

    def start_discord_bot(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Start the Discord bot using `start-discord-bot.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("start-discord-bot.ps1", timeout_seconds=timeout_seconds, check=check)

    def stop_discord_bot(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Stop the Discord bot using `stop-discord-bot.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("stop-discord-bot.ps1", timeout_seconds=timeout_seconds, check=check)

    def restart_discord_bot(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Restart the Discord bot using `restart-discord-bot.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("restart-discord-bot.ps1", timeout_seconds=timeout_seconds, check=check)

    def check_environment(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Run environment validation using `environment-check.ps1`.

        Returns:
            `ScriptResult` with at least one `STATUS|...` line in stdout.

        Raises:
            InvalidScriptOutputError: The script succeeds but returns no
                structured `STATUS|...` line.
            Broker exceptions from `run_script`.
        """

        return self._run_status_script("environment-check.ps1", timeout_seconds=timeout_seconds, check=check)

    def start_all(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Start the full ScenarioRP environment using `start-all.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("start-all.ps1", timeout_seconds=timeout_seconds, check=check)

    def close_server_shell(self, *, timeout_seconds: float | None = None, check: bool = True) -> ScriptResult:
        """Close the FXServer shell using `close-server-shell.ps1`.

        Returns:
            `ScriptResult` from the script execution.

        Raises:
            Broker exceptions from `run_script`.
        """

        return self.run_script("close-server-shell.ps1", timeout_seconds=timeout_seconds, check=check)

    def _run_status_script(
        self,
        script_name: str,
        *,
        timeout_seconds: float | None,
        check: bool,
    ) -> ScriptResult:
        result = self.run_script(script_name, timeout_seconds=timeout_seconds, check=check)
        if result.success and not result.status_lines:
            raise InvalidScriptOutputError(
                script_name,
                "expected at least one structured STATUS line",
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result

    def _script_path(self, script_name: str) -> Path:
        if not script_name or Path(script_name).is_absolute() or Path(script_name).suffix.lower() != ".ps1":
            raise InvalidScriptNameError(script_name)

        scripts_root = self.scripts_dir.resolve()
        script_path = (scripts_root / script_name).resolve()
        try:
            script_path.relative_to(scripts_root)
        except ValueError as exc:
            raise InvalidScriptNameError(script_name) from exc

        if not script_path.is_file():
            raise ScriptNotFoundError(script_name, script_path)

        return script_path

    @staticmethod
    def _decode_timeout_output(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
