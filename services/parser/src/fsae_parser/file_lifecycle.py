from pathlib import Path
import shutil


class FileLifecycle:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.uploaded_dir = data_root / "uploaded"
        self.processing_dir = data_root / "processing"
        self.processed_dir = data_root / "processed"
        self.failed_dir = data_root / "failed"

    def ensure_dirs(self) -> None:
        for directory in [
            self.uploaded_dir,
            self.processing_dir,
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
                and not path.name.startswith(".")
            )
        )

    def move_to_processing(self, source_path: Path) -> Path:
        destination_path = self.processing_dir / source_path.name
        return source_path.rename(destination_path)

    def move_to_processed(self, source_path: Path) -> Path:
        destination_path = self.processed_dir / source_path.name
        return source_path.rename(destination_path)

    def move_to_failed(self, source_path: Path) -> Path:
        destination_path = self.failed_dir / source_path.name
        return source_path.rename(destination_path)