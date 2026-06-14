"""
Purpose:
Loads configuration for the Loki exporter service from environment variables.

The exporter needs access to the shared data folder and Grafana Cloud Loki
credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class LokiExporterConfig:
    data_root: Path
    loki_push_url: str
    loki_user: str
    loki_token: str
    poll_interval_seconds: float
    batch_size: int


def load_config() -> LokiExporterConfig:
    return LokiExporterConfig(
        data_root=Path(os.getenv("DATA_ROOT", "/app/data")),
        loki_push_url=os.environ["GRAFANA_LOKI_PUSH_URL"],
        loki_user=os.environ["GRAFANA_LOKI_USER"],
        loki_token=os.environ["GRAFANA_CLOUD_TOKEN"],
        poll_interval_seconds=float(
            os.getenv("LOKI_EXPORTER_POLL_INTERVAL_SECONDS", "2")
        ),
        batch_size=int(os.getenv("LOKI_EXPORTER_BATCH_SIZE", "1000")),
    )