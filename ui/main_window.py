from __future__ import annotations

from datetime import datetime
import re
from typing import TypeVar

from PySide6.QtCore import QFile, QTimer
from PySide6.QtGui import QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QLabel, QMainWindow, QPlainTextEdit, QPushButton, QWidget

from core.config import AppConfig
from core.paths import AppPaths
from services.script_runner import ScriptResult, ScriptRunner


WidgetT = TypeVar("WidgetT", bound=QWidget)
SCRIPT_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ")


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, paths: AppPaths) -> None:
        super().__init__()
        self.config = config
        self.paths = paths
        scripts_dir = paths.manager_dir / "scripts"
        self.action_runner = ScriptRunner(scripts_dir, self)
        self.status_runner = ScriptRunner(scripts_dir, self)

        self._load_designer_ui()
        self._load_styles()
        self._bind_widgets()
        self._connect_signals()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(4000)
        self.refresh_status()

    def _load_designer_ui(self) -> None:
        ui_path = self.paths.manager_dir / "ui" / "main_window.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Could not open UI file: {ui_path}")

        self._ui_loader = QUiLoader()
        loaded = self._ui_loader.load(ui_file, self)
        ui_file.close()
        if loaded is None:
            raise RuntimeError(f"Could not load UI file: {ui_path}")
        if not isinstance(loaded, QWidget):
            raise RuntimeError(f"Expected QWidget in UI file: {ui_path}")

        self.setWindowTitle("ScenarioRP Manager")
        self.resize(loaded.size())
        self.setCentralWidget(loaded)
        self._designer_widget = loaded

    def _load_styles(self) -> None:
        qss_path = self.paths.manager_dir / "ui" / "styles.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _widget(self, name: str, widget_type: type[WidgetT]) -> WidgetT:
        widget = self.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Missing widget in main_window.ui: {name}")
        return widget

    def _bind_widgets(self) -> None:
        self.project_root_label = self._widget("projectRootLabel", QLabel)
        self.start_button = self._widget("startButton", QPushButton)
        self.stop_button = self._widget("stopButton", QPushButton)
        self.restart_button = self._widget("restartButton", QPushButton)
        self.safe_shutdown_button = self._widget("safeShutdownButton", QPushButton)
        self.txadmin_button = self._widget("txadminButton", QPushButton)

        self.fx_state_label = self._widget("fxStateLabel", QLabel)
        self.fx_message_label = self._widget("fxMessageLabel", QLabel)
        self.bot_state_label = self._widget("botStateLabel", QLabel)
        self.bot_message_label = self._widget("botMessageLabel", QLabel)
        self.environment_state_label = self._widget("environmentStateLabel", QLabel)
        self.environment_message_label = self._widget("environmentMessageLabel", QLabel)
        self.txadmin_state_label = self._widget("txadminStateLabel", QLabel)
        self.txadmin_message_label = self._widget("txadminMessageLabel", QLabel)
        self.database_state_label = self._widget("databaseStateLabel", QLabel)
        self.database_message_label = self._widget("databaseMessageLabel", QLabel)
        self.log_viewer = self._widget("logViewer", QPlainTextEdit)

        self.project_root_label.setText(str(self.paths.project_root))
        self.log_viewer.setFont(QFont("Consolas", 10))
        self.log_viewer.setReadOnly(True)

    def _connect_signals(self) -> None:
        self.action_runner.output.connect(self.append_output)
        self.action_runner.finished.connect(self.action_finished)
        self.status_runner.finished.connect(self.status_finished)
        self.start_button.clicked.connect(lambda: self.run_script("start-server.ps1"))
        self.stop_button.clicked.connect(lambda: self.run_script("stop-server.ps1"))
        self.restart_button.clicked.connect(lambda: self.run_script("restart-server.ps1"))
        self.safe_shutdown_button.clicked.connect(lambda: self.run_script("safe-shutdown.ps1"))
        self.txadmin_button.clicked.connect(lambda: self.run_script("open-txadmin.ps1"))

    def append_output(self, text: str) -> None:
        if not text:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for line in text.splitlines():
            if SCRIPT_TIMESTAMP_RE.match(line):
                self.log_viewer.appendPlainText(line)
            else:
                self.log_viewer.appendPlainText(f"{timestamp} | {line}")
        self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())

    def run_script(self, script_name: str) -> None:
        if self.action_runner.run_script(script_name):
            self._set_actions_enabled(False)

    def refresh_status(self) -> None:
        if self.status_runner.is_running():
            return
        self.status_runner.run_script("status.ps1", show_output=False)

    def action_finished(self, result: ScriptResult) -> None:
        self._set_actions_enabled(True)
        if result.script_name != "open-txadmin.ps1":
            self.refresh_status()

    def status_finished(self, result: ScriptResult) -> None:
        self._apply_status_output(result.stdout)

    def _apply_status_output(self, stdout: str) -> None:
        for line in stdout.splitlines():
            parts = line.split("|", 3)
            if len(parts) != 4 or parts[0] != "STATUS":
                continue
            _, name, state, message = parts
            self._set_status_card(name, state, message)

    def _set_status_card(self, name: str, state: str, message: str) -> None:
        if name == "FXServer":
            self._set_status(self.fx_state_label, self.fx_message_label, state, message)
        elif name == "Discord Bot":
            self._set_status(self.bot_state_label, self.bot_message_label, state, message)
        elif name == "txAdmin":
            self._set_status(self.txadmin_state_label, self.txadmin_message_label, state, message)
        elif name == "Database":
            self._set_status(self.database_state_label, self.database_message_label, state, message)

        self._set_status(self.environment_state_label, self.environment_message_label, "OK", "Use environment-check.ps1 for details")

    def _set_status(self, state_label: QLabel, message_label: QLabel, state: str, message: str) -> None:
        state_label.setText(state)
        message_label.setText(message)

    def _set_actions_enabled(self, enabled: bool) -> None:
        for button in [self.start_button, self.stop_button, self.restart_button, self.safe_shutdown_button, self.txadmin_button]:
            button.setEnabled(enabled)
