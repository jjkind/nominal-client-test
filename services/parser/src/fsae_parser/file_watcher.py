"""
Purpose:
Runs the parser worker loop.

This module watches the uploaded folder, moves new files into processing,
parses them, normalizes their records, writes the requested output format, and
then moves the original file to processed or failed.
"""

from __future__ import annotations

from pathlib import Path
import time

from fsae_parser.file_lifecycle import FileLifecycle
from fsae_parser.normalizers import TelemetryNormalizer
from fsae_parser.output_writers import TelemetryOutputWriter
from fsae_parser.parsers import FsaeBinaryParser


class FileWatcher:
    def __init__(self, data_root: Path, poll_interval_seconds: float = 2.0) -> None:
        self.lifecycle = FileLifecycle(data_root)
        self.poll_interval_seconds = poll_interval_seconds
        self.parser = FsaeBinaryParser()
        self.normalizer = TelemetryNormalizer(car="fsae_demo")
        self.output_writer = TelemetryOutputWriter()

    def run_forever(self) -> None:
        self.lifecycle.ensure_dirs()

        print("Parser worker started.", flush=True)
        print(f"Watching for files in: {self.lifecycle.uploaded_dir}", flush=True)

        while True:
            uploaded_files = self.lifecycle.list_uploaded_files()

            for uploaded_file in uploaded_files:
                self.process_file(uploaded_file)

            time.sleep(self.poll_interval_seconds)

    def process_file(self, uploaded_file: Path) -> None:
        print(f"Found uploaded file: {uploaded_file.name}", flush=True)

        processing_file = self.lifecycle.move_to_processing(uploaded_file)
        print(f"Moved to processing: {processing_file}", flush=True)

        output_format = self.lifecycle.output_format_for(processing_file)
        normalized_path = self.lifecycle.normalized_output_path_for(
            source_path=processing_file,
            output_format=output_format,
        )
        temp_normalized_path = normalized_path.with_suffix(
            normalized_path.suffix + ".tmp"
        )

        try:
            packets = self.parser.parse_file(processing_file)
            records = self.normalizer.normalize_packets(packets)

            record_count = self.output_writer.write(
                records=records,
                output_format=output_format,
                temp_path=temp_normalized_path,
                final_path=normalized_path,
            )

            print(
                f"Wrote {record_count} records to {normalized_path} "
                f"using output_format={output_format}",
                flush=True,
            )

            processed_file = self.lifecycle.move_to_processed(processing_file)
            print(f"Moved to processed: {processed_file}", flush=True)

        except Exception as exc:
            print(f"Failed to process {processing_file.name}: {exc}", flush=True)

            if temp_normalized_path.exists():
                temp_normalized_path.unlink()

            failed_file = self.lifecycle.move_to_failed(processing_file)
            print(f"Moved to failed: {failed_file}", flush=True)