"""
Purpose:
Defines shared data models used by the parser, normalizer, and future exporters.

ParsedPacket represents one decoded packet from the binary Formula SAE file.
TelemetryRecord represents one normalized telemetry value ready for downstream
export to Loki, Nominal, Elasticsearch, or another backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


TelemetryValue = float | int | bool | str


@dataclass(frozen=True)
class ParsedPacket:
    """
    One decoded packet from the Formula SAE binary file.

    This is parser output, not exporter-ready output.
    """

    session_id: str
    session_start_unix_ms: int
    timestamp_ms: int
    channel_id: int
    subsystem: str
    values: Mapping[str, TelemetryValue]
    units: Mapping[str, str]
    source_file: str | None = None


@dataclass(frozen=True)
class TelemetryRecord:
    """
    Backend-neutral normalized telemetry record.

    Loki, Nominal, and Elasticsearch exporters should eventually consume this
    format instead of consuming binary parser structures directly.
    """

    timestamp_ns: int
    session_id: str
    car: str
    subsystem: str
    channel: str
    value: TelemetryValue
    units: str
    source_file: str | None = None