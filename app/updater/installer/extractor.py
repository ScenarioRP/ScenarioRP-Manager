from __future__ import annotations

from pathlib import Path


class UpdateExtractor:
    """Interface for extracting downloaded update ZIP files."""

    def extract(self, zip_path: Path) -> Path:
        """Extract zip_path and return the extracted package directory."""
        raise NotImplementedError("ZIP extraction is not implemented yet.")
