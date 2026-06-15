"""
Purpose:
Runs the Loki exporter worker loop.

This module watches data/normalized for JSONL files produced by the parser
service, exports each file to Loki, and writes status marker files under
data/export_status/loki/.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import time
from typing import Any

from .config import LokiExporterConfig
from .loki_client import LokiClient


class LokiExportWorker:
    def __init__(self, config: LokiExporterConfig) -> None:
        self.config = config
        self.normalized_dir = config.data_root / "normalized"
        self.exported_dir = config.data_root / "export_status" / "loki" / "exported"
        self.failed_dir = config.data_root / "export_status" / "loki" / "failed"

        self.client = LokiClient(
            push_url=config.loki_push_url,
            username=config.loki_user,
            token=config.loki_token,
        )

    def run_forever(self) -> None:
        self.ensure_dirs()

        print("Loki exporter started.", flush=True)
        print(f"Watching normalized files in: {self.normalized_dir}", flush=True)

        while True:
            for path in self.list_pending_files():
                self.export_file(path)

            time.sleep(self.config.poll_interval_seconds)

    def ensure_dirs(self) -> None:
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        self.exported_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def list_pending_files(self) -> list[Path]:
        exported_markers = {path.name for path in self.exported_dir.glob("*.success")}
        failed_markers = {path.name for path in self.failed_dir.glob("*.failed")}

        return sorted(
            path
            for path in self.normalized_dir.glob("*.jsonl")
            if (
                not path.name.startswith(".")
                and f"{path.name}.success" not in exported_markers
                and f"{path.name}.failed" not in failed_markers
            )
        )

    def export_file(self, path: Path) -> None:
        try:
            exported_count = 0

            for batch in self._read_jsonl_batches(
                path=path,
                batch_size=self.config.batch_size,
            ):
                exported_count += self.client.push_records(batch)

            self._write_status_file(
                path=self.exported_dir / f"{path.name}.success",
                content=f"exported_records={exported_count}\n",
            )

            print(
                f"Exported {exported_count} records from {path.name} to Loki.",
                flush=True,
            )

        except Exception as exc:
            self._write_status_file(
                path=self.failed_dir / f"{path.name}.failed",
                content=f"error={exc}\n",
            )

            print(
                f"Failed to export {path.name} to Loki: {exc}",
                flush=True,
            )

    @staticmethod
    def _read_jsonl_batches(
        path: Path,
        batch_size: int,
    ) -> Iterator[list[dict[str, Any]]]:
        batch: list[dict[str, Any]] = []

        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                batch.append(json.loads(line))

                if len(batch) >= batch_size:
                    yield batch
                    batch = []

        if batch:
            yield batch

    @staticmethod
    def _write_status_file(path: Path, content: str) -> None:
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.rename(path)