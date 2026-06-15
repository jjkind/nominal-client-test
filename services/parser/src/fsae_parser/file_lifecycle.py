"""
Purpose:
Manages the local file lifecycle for uploaded telemetry files.

This module owns the shared data folder locations and provides helper methods
for moving files through uploaded, processing, normalized, processed, and failed
states.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_OUTPUT_FORMATS = {"jsonl", "parquet", "dataframe"}
OUTPUT_EXTENSIONS = {
    "jsonl": ".jsonl",
    "parquet": ".parquet",
    "dataframe": ".csv",
}


class FileLifecycle:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.uploaded_dir = data_root / "uploaded"
        self.processing_dir = data_root / "processing"
        self.normalized_dir = data_root / "normalized"
        self.processed_dir = data_root / "processed"
        self.failed_dir = data_root / "failed"

    def ensure_dirs(self) -> None:
        for directory in [
            self.uploaded_dir,
            self.processing_dir,
            self.normalized_dir,
            self.processed_dir,
            self.failed_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def list_uploaded_files(self) -> list[Path]:
        self.ensure_dirs()

        return sorted(
            path
            for path in self.uploaded_dir.iterdir()
            if (
                path.is_file()
                and not path.name.endswith(".tmp")
                and not path.name.endswith(".metadata.json")
                and not path.name.startswith(".")
            )
        )

    def move_to_processing(self, source_path: Path) -> Path:
        destination_path = self.processing_dir / source_path.name
        metadata_path = self.metadata_path_for(source_path)

        if metadata_path.exists():
            metadata_destination_path = self.processing_dir / metadata_path.name
            metadata_path.rename(metadata_destination_path)

        return source_path.rename(destination_path)

    def move_to_processed(self, source_path: Path) -> Path:
        destination_path = self.processed_dir / source_path.name
        metadata_path = self.metadata_path_for(source_path)

        if metadata_path.exists():
            metadata_destination_path = self.processed_dir / metadata_path.name
            metadata_path.rename(metadata_destination_path)

        return source_path.rename(destination_path)

    def move_to_failed(self, source_path: Path) -> Path:
        destination_path = self.failed_dir / source_path.name
        metadata_path = self.metadata_path_for(source_path)

        if metadata_path.exists():
            metadata_destination_path = self.failed_dir / metadata_path.name
            metadata_path.rename(metadata_destination_path)

        return source_path.rename(destination_path)

    def metadata_path_for(self, source_path: Path) -> Path:
        return source_path.with_name(f"{source_path.name}.metadata.json")

    def read_metadata_for(self, source_path: Path) -> dict[str, Any]:
        metadata_path = self.metadata_path_for(source_path)

        if not metadata_path.exists():
            return {"output_format": "jsonl"}

        with metadata_path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)

        if not isinstance(metadata, dict):
            raise ValueError(f"Metadata file is not a JSON object: {metadata_path}")

        return metadata

    def output_format_for(self, source_path: Path) -> str:
        metadata = self.read_metadata_for(source_path)
        output_format = str(metadata.get("output_format", "jsonl"))

        if output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format={output_format!r} for {source_path.name}. "
                "Valid choices are: jsonl, parquet, dataframe."
            )

        return output_format

    def normalized_output_path_for(self, source_path: Path, output_format: str) -> Path:
        if output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format={output_format!r}. "
                "Valid choices are: jsonl, parquet, dataframe."
            )

        extension = OUTPUT_EXTENSIONS[output_format]
        return self.normalized_dir / f"{source_path.stem}{extension}"