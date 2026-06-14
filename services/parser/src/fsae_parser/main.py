"""
Purpose:
Entrypoint for the parser container.

This module reads the parser service configuration, creates the file watcher,
and starts the long-running parser worker process.
"""

from pathlib import Path
import os

from fsae_parser.file_watcher import FileWatcher


def main() -> None:
    data_root = Path(os.getenv("DATA_ROOT", "/app/data"))

    watcher = FileWatcher(
        data_root=data_root,
        poll_interval_seconds=2.0,
    )

    watcher.run_forever()


if __name__ == "__main__":
    main()