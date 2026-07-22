from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import zipfile

from app.updater.exceptions import UpdateExtractionError
from app.updater.installer.filesystem import safe_archive_target
from app.updater.installer.validator import UpdateValidator

class UpdateExtractor:
    """Interface for extracting downloaded update ZIP files."""

    def __init__(self, validator: UpdateValidator | None = None) -> None:
        self.validator = validator or UpdateValidator()

    def extract(self, zip_path: Path, extracted_root: Path) -> Path:
        """Extract zip_path and return the extracted package directory."""
        extracted_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="ScenarioRPUpdate-", dir=extracted_root))
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for entry in archive.infolist():
                    self.validator.validate_archive_member(entry)
                    target = safe_archive_target(temp_dir, entry.filename)
                    if entry.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry, "r") as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
            package_root = self.detect_package_root(temp_dir)
            self.validator.validate_extracted_package(package_root)
            return package_root
        except Exception as exc:
            self.cleanup(temp_dir)
            if isinstance(exc, UpdateExtractionError):
                raise
            raise UpdateExtractionError(f"Could not extract update ZIP: {zip_path}") from exc

    def detect_package_root(self, extracted_dir: Path) -> Path:
        """Detect direct-root or one-wrapper-folder package layout."""
        if (extracted_dir / "ScenarioRP-Manager.exe").is_file():
            return extracted_dir
        children = [child for child in extracted_dir.iterdir()]
        directories = [child for child in children if child.is_dir()]
        relevant_root_files = [child for child in children if child.is_file() and child.name == "ScenarioRP-Manager.exe"]
        if len(directories) == 1 and not relevant_root_files:
            return directories[0]
        return extracted_dir

    def cleanup(self, path: Path | None) -> None:
        """Delete extracted temporary files."""
        if path is not None:
            shutil.rmtree(path, ignore_errors=True)
