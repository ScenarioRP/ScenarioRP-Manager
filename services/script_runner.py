from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QObject, QProcess, Signal


@dataclass(frozen=True)
class ScriptResult:
    script_name: str
    exit_code: int
    elapsed_seconds: float
    stdout: str
    stderr: str


class ScriptRunner(QObject):
    output = Signal(str)
    finished = Signal(object)

    def __init__(self, scripts_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.scripts_dir = scripts_dir
        self.process: QProcess | None = None
        self.script_name = ""
        self.started_at = 0.0
        self.stdout_parts: list[str] = []
        self.stderr_parts: list[str] = []
        self.show_output = True

    def is_running(self) -> bool:
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def run_script(self, script_name: str, show_output: bool = True) -> bool:
        if self.is_running():
            if show_output:
                self.output.emit("ScriptRunner is busy.")
            return False

        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            if show_output:
                self.output.emit(f"Missing script: {script_path}")
            return False

        self.script_name = script_name
        self.show_output = show_output
        self.started_at = monotonic()
        self.stdout_parts = []
        self.stderr_parts = []

        process = QProcess(self)
        process.setProgram("powershell")
        process.setArguments(["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)])
        process.setWorkingDirectory(str(self.scripts_dir.parent))
        process.setProcessChannelMode(QProcess.SeparateChannels)
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._finished)
        self.process = process
        if self.show_output:
            self.output.emit(f"> {script_name}")
        process.start()
        return True

    def _read_stdout(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.stdout_parts.append(text)
        if text and self.show_output:
            self.output.emit(text.rstrip())

    def _read_stderr(self) -> None:
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self.stderr_parts.append(text)
        if text and self.show_output:
            self.output.emit(text.rstrip())

    def _finished(self, exit_code: int) -> None:
        result = ScriptResult(
            script_name=self.script_name,
            exit_code=exit_code,
            elapsed_seconds=monotonic() - self.started_at,
            stdout="".join(self.stdout_parts),
            stderr="".join(self.stderr_parts),
        )
        if self.show_output:
            self.output.emit(f"< {self.script_name} exited {exit_code} in {result.elapsed_seconds:.2f}s")
        self.process = None
        self.finished.emit(result)
