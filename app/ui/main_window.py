from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import re
from typing import TypeVar

from PySide6.QtCore import QFile, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEnginePage = None
    QWebEngineProfile = None
    QWebEngineView = None

from app.core.config import AppConfig
from app.paths import AppPaths
from app.services.process_monitor import ProcessMonitor, SystemStatus
from app.services.script_runner import ScriptResult, ScriptRunner
from app.ui.update import UpdateCheckWorker, UpdateDialog, UpdateDownloadWorker
from app.updater import (
    APP_VERSION,
    GitHubReleaseProvider,
    UpdateDownloader,
    UpdateManager,
    UpdateRelease,
    load_update_config,
)


WidgetT = TypeVar("WidgetT", bound=QWidget)
SCRIPT_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ")
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, paths: AppPaths) -> None:
        super().__init__()
        self.config = config
        self.paths = paths
        scripts_dir = paths.app_file("scripts")
        self.action_runner = ScriptRunner(scripts_dir, paths.manager_dir, paths.script_environment(), self)
        self.monitor = ProcessMonitor(config, paths)
        self._update_check_thread: QThread | None = None
        self._update_check_worker: UpdateCheckWorker | None = None
        self._update_download_thread: QThread | None = None
        self._update_download_worker: UpdateDownloadWorker | None = None
        self._update_dialog: UpdateDialog | None = None
        self._update_manager: UpdateManager | None = None
        self._manual_update_check = False
        self.web_view: QWebEngineView | None = None
        self.web_profile: QWebEngineProfile | None = None
        self._txadmin_loaded = False
        self._external_txadmin_fallback_used = False

        self._load_designer_ui()
        self._load_styles()
        self._bind_widgets()
        self._setup_txadmin_view()
        self._connect_signals()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(4000)
        self.refresh_status()
        QTimer.singleShot(0, self._maybe_check_for_updates_on_startup)

    def _load_designer_ui(self) -> None:
        ui_path = self.paths.app_file("ui", "main_window.ui")
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
        qss_path = self.paths.app_file("ui", "styles.qss")
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _widget(self, name: str, widget_type: type[WidgetT]) -> WidgetT:
        widget = self.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"Missing widget in main_window.ui: {name}")
        return widget

    def _bind_widgets(self) -> None:
        self.project_root_label = self._widget("projectRootLabel", QLabel)
        self.header_status_label = self._widget("headerStatusLabel", QLabel)
        self.module_tabs = self._widget("moduleTabs", QTabWidget)
        self.dashboard_terminal_label = self._widget("dashboardTerminalLabel", QLabel)
        self.start_button = self._widget("startButton", QPushButton)
        self.finish_shutdown_button = self._widget("finishShutdownButton", QPushButton)
        self.dashboard_server_state_label = self._widget("dashboardServerStateLabel", QLabel)
        self.dashboard_discord_state_label = self._widget("dashboardDiscordStateLabel", QLabel)
        self.dashboard_database_state_label = self._widget("dashboardDatabaseStateLabel", QLabel)
        self.txadmin_tab = self._widget("txadminTab", QWidget)
        self.txadmin_container = self._widget("txadminContainer", QWidget)
        self.settings_tab = self._widget("settingsTab", QWidget)
        self.log_viewer = self._widget("logViewer", QPlainTextEdit)

        self.project_root_label.setText(str(self.paths.resolve_project_path(self.config.fxserver_exe)))
        self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Ready.")
        self.finish_shutdown_button.setEnabled(False)
        self.log_viewer.setFont(QFont("Consolas", 10))
        self.log_viewer.setReadOnly(True)
        self.check_updates_button = QPushButton("Check for updates", self.settings_tab)
        settings_layout = self.settings_tab.layout()
        if settings_layout is not None:
            self.settings_version_label = QLabel(f"Version: v{APP_VERSION}", self.settings_tab)
            settings_layout.addWidget(self.settings_version_label)
            settings_layout.addWidget(self.check_updates_button)

    def _setup_txadmin_view(self) -> None:
        layout = self.txadmin_container.layout()
        if layout is None:
            layout = QVBoxLayout(self.txadmin_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if QWebEngineView is None or QWebEngineProfile is None or QWebEnginePage is None:
            fallback_label = QLabel("txAdmin will open externally if Qt WebEngine is unavailable.")
            fallback_label.setWordWrap(True)
            layout.addWidget(fallback_label)
            return

        self.web_view = QWebEngineView(self.txadmin_container)
        self.web_profile = self._create_txadmin_web_profile()
        self.web_view.setPage(QWebEnginePage(self.web_profile, self.web_view))
        self.web_view.loadFinished.connect(self._txadmin_load_finished)
        layout.addWidget(self.web_view)

    def _create_txadmin_web_profile(self) -> QWebEngineProfile:
        profile_dir = self._web_profile_dir()
        cache_dir = profile_dir / "Cache"
        try:
            profile_dir.mkdir(parents=True, exist_ok=True)
            cache_dir.mkdir(parents=True, exist_ok=True)

            profile = QWebEngineProfile("ScenarioRP-Manager", self)
            profile.setPersistentStoragePath(str(profile_dir))
            profile.setCachePath(str(cache_dir))
            profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
            profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            return profile
        except (OSError, RuntimeError) as exc:
            self.append_output(f"Persistent txAdmin browser profile is unavailable: {exc}. Using a fresh browser session.")
            return QWebEngineProfile(self)

    def _web_profile_dir(self) -> Path:
        return self.paths.user("cache", "WebProfile")

    def _connect_signals(self) -> None:
        self.action_runner.output.connect(self.append_output)
        self.action_runner.finished.connect(self.action_finished)
        self.start_button.clicked.connect(self.start_server)
        self.finish_shutdown_button.clicked.connect(self.close_server_shell)
        self.check_updates_button.clicked.connect(self.check_for_updates_manually)

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

    def check_for_updates_manually(self) -> None:
        self._start_update_check(manual=True)

    def _maybe_check_for_updates_on_startup(self) -> None:
        try:
            update_config = load_update_config(self.paths.update_config)
        except Exception as exc:
            LOGGER.warning("Could not load update config: %s", exc)
            return

        if update_config.check_on_startup:
            self._start_update_check(manual=False)

    def _start_update_check(self, manual: bool) -> None:
        if self._update_check_thread is not None:
            if manual:
                QMessageBox.information(self, "בדיקת עדכונים", "בדיקת עדכונים כבר פעילה.")
            return

        try:
            self._update_manager = self._create_update_manager()
        except Exception as exc:
            LOGGER.warning("Could not initialize update manager: %s", exc)
            if manual:
                QMessageBox.warning(self, "שגיאת עדכונים", str(exc))
            return

        self._manual_update_check = manual
        self.check_updates_button.setEnabled(False)

        thread = QThread(self)
        worker = UpdateCheckWorker(self._update_manager)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.update_available.connect(self._update_available)
        worker.no_update.connect(self._no_update_available)
        worker.error.connect(self._update_check_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._update_check_finished)

        self._update_check_thread = thread
        self._update_check_worker = worker
        thread.start()

    def _create_update_manager(self) -> UpdateManager:
        update_config = load_update_config(self.paths.update_config)
        provider = GitHubReleaseProvider(
            repository=update_config.repository,
            allow_prerelease=update_config.allow_prerelease,
            timeout_seconds=update_config.request_timeout_seconds,
        )
        downloader = UpdateDownloader(timeout_seconds=update_config.request_timeout_seconds)
        return UpdateManager(provider=provider, downloader=downloader, current_version=APP_VERSION)

    def _update_available(self, release: UpdateRelease) -> None:
        self._show_update_dialog(release)

    def _no_update_available(self) -> None:
        if self._manual_update_check:
            QMessageBox.information(self, "בדיקת עדכונים", "התוכנה מעודכנת.")

    def _update_check_error(self, message: str) -> None:
        LOGGER.warning("Update check failed: %s", message)
        if self._manual_update_check:
            QMessageBox.warning(self, "שגיאת עדכונים", message)

    def _update_check_finished(self) -> None:
        self._update_check_thread = None
        self._update_check_worker = None
        self._manual_update_check = False
        self.check_updates_button.setEnabled(True)

    def _show_update_dialog(self, release: UpdateRelease) -> None:
        dialog = UpdateDialog(APP_VERSION, release, self)
        dialog.download_requested.connect(self._download_update)
        self._update_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _download_update(self, release: UpdateRelease) -> None:
        if self._update_download_thread is not None:
            return
        if self._update_manager is None:
            try:
                self._update_manager = self._create_update_manager()
            except Exception as exc:
                LOGGER.warning("Could not initialize update downloader: %s", exc)
                if self._update_dialog is not None:
                    self._update_dialog.show_download_error(str(exc))
                return

        thread = QThread(self)
        worker = UpdateDownloadWorker(self._update_manager, release, self.paths.update_downloads)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._download_progress)
        worker.completed.connect(self._download_completed)
        worker.error.connect(self._download_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._download_finished)

        self._update_download_thread = thread
        self._update_download_worker = worker
        thread.start()

    def _download_progress(self, downloaded_bytes: int, total_bytes: int, percent: int) -> None:
        if self._update_dialog is not None:
            self._update_dialog.set_download_progress(downloaded_bytes, total_bytes, percent)

    def _download_completed(self, path: object) -> None:
        if self._update_dialog is not None and isinstance(path, Path):
            self._update_dialog.show_download_finished(path)

    def _download_error(self, message: str) -> None:
        LOGGER.warning("Update download failed: %s", message)
        if self._update_dialog is not None:
            self._update_dialog.show_download_error(message)

    def _download_finished(self) -> None:
        self._update_download_thread = None
        self._update_download_worker = None

    def run_script(self, script_name: str) -> None:
        if self.action_runner.run_script(script_name):
            self._set_action_buttons_enabled(False, False)

    def start_server(self) -> None:
        self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Starting FXServer...\n> Waiting for txAdmin...")
        self.run_script("start-all.ps1")

    def close_server_shell(self) -> None:
        if not self.monitor.server_is_offline():
            self.append_output("Close Shell is disabled until the server port is offline.")
            self.refresh_status()
            return
        self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Closing server shell...")
        self.run_script("close-server-shell.ps1")

    def refresh_status(self) -> None:
        status = self.monitor.collect()
        self._apply_status(status)

    def action_finished(self, result: ScriptResult) -> None:
        self.refresh_status()
        if result.script_name == "start-all.ps1" and result.exit_code == 0:
            self.load_txadmin()
            self.module_tabs.setCurrentWidget(self.txadmin_tab)
        elif result.script_name == "close-server-shell.ps1":
            self.refresh_status()

    def _apply_status(self, status: SystemStatus) -> None:
        fx_running = status.fxserver.state == "Running"
        server_offline = status.server.state == "Offline"

        self._set_header_status(status)
        self.dashboard_server_state_label.setText(self._format_status(status.server))
        self.dashboard_discord_state_label.setText(self._format_status(status.discord_bot))
        self.dashboard_database_state_label.setText(self._format_status(status.database))

        if not self.action_runner.is_running():
            if status.server.state == "Online":
                self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Server Running.")
            elif status.server.state == "Offline":
                self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Server Stopped.")
            elif fx_running:
                self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Waiting for server status...")
            else:
                self.dashboard_terminal_label.setText("> ScenarioRP Environment\n> Ready.")

        if status.txadmin.state == "Running" and not self._txadmin_loaded:
            self.load_txadmin()

        if not self.action_runner.is_running():
            self._set_action_buttons_enabled(
                start_enabled=not fx_running,
                finish_enabled=server_offline,
            )

    def _format_status(self, status: object) -> str:
        name = getattr(status, "name")
        state = getattr(status, "state")
        message = getattr(status, "message")
        return f"{name}: {state} ({message})"

    def _set_header_status(self, status: SystemStatus) -> None:
        if status.server.state == "Online":
            text = "online 🟢"
            state = "running"
        elif status.server.state == "Offline":
            text = "offline 🔴"
            state = "stopped"
        elif status.server.state == "Starting":
            text = "starting 🟡"
            state = "starting"
        else:
            text = "offline 🔴"
            state = "stopped"

        self.header_status_label.setText(text)
        self.setWindowTitle(f"ScenarioRP Manager - {text}")
        self.header_status_label.setProperty("serverState", state)
        self.header_status_label.style().unpolish(self.header_status_label)
        self.header_status_label.style().polish(self.header_status_label)

    def _set_action_buttons_enabled(self, start_enabled: bool, finish_enabled: bool) -> None:
        self.start_button.setEnabled(start_enabled)
        self.finish_shutdown_button.setEnabled(finish_enabled)

    def load_txadmin(self) -> None:
        if self.web_view is None:
            self._open_txadmin_externally_once("Qt WebEngine is unavailable.")
            return

        self._txadmin_loaded = True
        self.web_view.load(QUrl(self.config.txadmin_url))
        self.append_output(f"Loading txAdmin in ScenarioRP Manager: {self.config.txadmin_url}")

    def _txadmin_load_finished(self, ok: bool) -> None:
        if ok:
            return
        self._open_txadmin_externally_once("Embedded txAdmin failed to load.")

    def _open_txadmin_externally_once(self, reason: str) -> None:
        if self._external_txadmin_fallback_used:
            return
        self._external_txadmin_fallback_used = True
        self.append_output(f"{reason} Opening txAdmin externally: {self.config.txadmin_url}")
        QDesktopServices.openUrl(QUrl(self.config.txadmin_url))
