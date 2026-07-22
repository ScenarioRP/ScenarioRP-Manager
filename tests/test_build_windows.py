from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts import build_windows


def write_file(path: Path, text: str = "data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_valid_distribution(root: Path) -> None:
    write_file(root / "ScenarioRP-Manager.exe", "manager")
    write_file(root / "ScenarioRPUpdater.exe", "updater")
    (root / "_internal").mkdir(parents=True)
    write_file(root / "assets" / "myLogo.png", "png")
    write_file(root / "system_data" / "config.json", "{}")
    write_file(root / "system_data" / "update_config.json", "{}")
    build_windows.create_clean_user_data(root / "user_data")


class WindowsBuildHelperTests(unittest.TestCase):
    def test_read_app_version_uses_existing_source(self) -> None:
        self.assertEqual(build_windows.read_app_version(), "0.1.1")

    def test_validate_distribution_accepts_clean_portable_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "ScenarioRP-Manager"
            create_valid_distribution(root)

            build_windows.validate_distribution(root)

    def test_validate_distribution_rejects_development_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "ScenarioRP-Manager"
            create_valid_distribution(root)
            (root / ".venv").mkdir()

            with self.assertRaises(build_windows.BuildError):
                build_windows.validate_distribution(root)

    def test_validate_distribution_rejects_personal_user_data_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "ScenarioRP-Manager"
            create_valid_distribution(root)
            write_file(root / "user_data" / "settings.json", "{}")

            with self.assertRaises(build_windows.BuildError):
                build_windows.validate_distribution(root)

    def test_validate_distribution_rejects_downloaded_update_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "ScenarioRP-Manager"
            create_valid_distribution(root)
            write_file(root / "user_data" / "updates" / "downloads" / "update.zip", "zip")

            with self.assertRaises(build_windows.BuildError):
                build_windows.validate_distribution(root)

    def test_zip_archive_contains_wrapper_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original_dist = build_windows.DIST_DIR
            try:
                build_windows.DIST_DIR = Path(directory)
                root = build_windows.DIST_DIR / "ScenarioRP-Manager"
                create_valid_distribution(root)

                zip_path = build_windows.create_zip_archive(root, "9.9.9")

                self.assertTrue(zip_path.is_file())
                import zipfile

                with zipfile.ZipFile(zip_path) as archive:
                    names = set(archive.namelist())
                self.assertIn("ScenarioRP-Manager/ScenarioRP-Manager.exe", names)
                self.assertIn("ScenarioRP-Manager/system_data/config.json", names)
            finally:
                build_windows.DIST_DIR = original_dist


if __name__ == "__main__":
    unittest.main()
