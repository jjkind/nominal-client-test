from pathlib import Path
import time

from .file_lifecycle import FileLifecycle


class FileWatcher:
    def __init__(self, data_root: Path, poll_interval_seconds: float = 2.0) -> None:
        self.lifecycle = FileLifecycle(data_root)
        self.poll_interval_seconds = poll_interval_seconds

    def run_forever(self) -> None:
        self.lifecycle.ensure_dirs()

        print("Parser worker started.")
        print(f"Watching for files in: {self.lifecycle.uploaded_dir}")

        while True:
            uploaded_files = self.lifecycle.list_uploaded_files()

            for uploaded_file in uploaded_files:
                self.process_file(uploaded_file)

            time.sleep(self.poll_interval_seconds)

    def process_file(self, uploaded_file: Path) -> None:
        print(f"Found uploaded file: {uploaded_file.name}")

        processing_file = self.lifecycle.move_to_processing(uploaded_file)
        print(f"Moved to processing: {processing_file}")

        try:
            # Placeholder for the real Formula SAE parser.
            # For now, just verify the file exists and can be read.
            file_size_bytes = processing_file.stat().st_size
            print(
                f"Placeholder processing complete for {processing_file.name}. "
                f"Size: {file_size_bytes} bytes"
            )

            processed_file = self.lifecycle.move_to_processed(processing_file)
            print(f"Moved to processed: {processed_file}")

        except Exception as exc:
            print(f"Failed to process {processing_file.name}: {exc}")

            failed_file = self.lifecycle.move_to_failed(processing_file)
            print(f"Moved to failed: {failed_file}")