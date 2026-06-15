"""
Purpose:
Builds Loki Push API payloads from normalized telemetry records and sends them
to Grafana Cloud Loki.

This module does not know anything about the original Formula SAE binary file.
It only understands normalized telemetry dictionaries loaded from JSONL files.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
import json
import time
from typing import Any

import requests


class LokiClient:
    def __init__(
        self,
        push_url: str,
        username: str,
        token: str,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.push_url = push_url
        self.auth = (username, token)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def push_records(self, records: Iterable[dict[str, Any]]) -> int:
        streams = self._build_streams(records)

        if not streams:
            return 0

        payload = {"streams": streams}
        record_count = self._count_records_in_streams(streams)

        self._post_with_retries(payload=payload)

        return record_count

    def _post_with_retries(self, payload: dict[str, Any]) -> None:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(
                    self.push_url,
                    json=payload,
                    auth=self.auth,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout_seconds,
                )

                if response.ok:
                    return

                response.raise_for_status()

            except requests.Timeout as exc:
                last_error = exc

            except requests.RequestException as exc:
                last_error = exc

            if attempt < self.max_retries:
                sleep_seconds = 2 ** (attempt - 1)
                time.sleep(sleep_seconds)

        raise RuntimeError(
            f"Failed to push records to Loki after {self.max_retries} attempts: "
            f"{last_error}"
        ) from last_error

    @staticmethod
    def _build_streams(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped_values: dict[tuple[tuple[str, str], ...], list[list[str]]] = (
            defaultdict(list)
        )

        for record in records:
            labels = {
                "app": "fsae-telemetry",
                "car": str(record["car"]),
                "session_id": str(record["session_id"]),
                "subsystem": str(record["subsystem"]),
                "channel": str(record["channel"]),
            }

            label_key = tuple(sorted(labels.items()))

            log_body = {
                "channel": record["channel"],
                "value": record["value"],
                "units": record["units"],
            }

            grouped_values[label_key].append(
                [
                    str(record["timestamp_ns"]),
                    json.dumps(log_body, separators=(",", ":")),
                ]
            )

        streams = []

        for label_key, values in grouped_values.items():
            values.sort(key=lambda item: int(item[0]))

            streams.append(
                {
                    "stream": dict(label_key),
                    "values": values,
                }
            )

        return streams

    @staticmethod
    def _count_records_in_streams(streams: list[dict[str, Any]]) -> int:
        return sum(len(stream["values"]) for stream in streams)