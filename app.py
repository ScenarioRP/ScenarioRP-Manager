from __future__ import annotations

import os
import sys

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    " ".join(
        [
            "--disable-gpu",
            "--disable-gpu-compositing",
            "--disable-accelerated-2d-canvas",
            "--disable-accelerated-video-decode",
        ]
    ),
)
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.config import load_config
from core.paths import AppPaths
from ui.main_window import MainWindow


def main() -> int:
    paths = AppPaths.discover()
    config = load_config(paths.manager_dir / "config.json")

    software_opengl = getattr(Qt.ApplicationAttribute, "AA_UseSoftwareOpenGL", None)
    if software_opengl is not None:
        QApplication.setAttribute(software_opengl, True)

    app = QApplication(sys.argv)
    icon_path = paths.resolve_project_path("txData/ScenarioRP/myLogo.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(config=config, paths=paths)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
