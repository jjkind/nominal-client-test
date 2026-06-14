"""
Purpose:
Entrypoint for the Loki exporter container.

This module loads configuration, creates the Loki export worker, and starts the
long-running watcher process.
"""

from .config import load_config
from .file_watcher import LokiExportWorker


def main() -> None:
    config = load_config()
    worker = LokiExportWorker(config)
    worker.run_forever()


if __name__ == "__main__":
    main()