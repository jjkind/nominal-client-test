from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


TelemetryValue = float | int | bool | str


@dataclass(frozen=True)
class ParsedPacket:
    """
    Backend-neutral representation of one decoded packet from the parser.

    The parser should produce this after decoding the binary payload for a
    specific channel.

    Example:
        channel_id=1
        subsystem="battery"
        values={
            "pack_voltage_v": 395.3,
            "pack_current_a": 87.8,
            "soc_pct": 95.9,
        }
        units={
            "pack_voltage_v": "V",
            "pack_current_a": "A",
            "soc_pct": "%",
        }
    """

    session_id: str
    session_start_unix_ms: int
    timestamp_ms: int
    channel_id: int
    subsystem: str
    values: Mapping[str, TelemetryValue]
    units: Mapping[str, str]
    source_file: Path | None = None


@dataclass(frozen=True)
class TelemetryRecord:
    """
    Standard normalized telemetry record used by all exporters.

    Exporters should consume this format instead of consuming parser-specific
    binary structures directly.
    """

    timestamp_ns: int
    session_id: str
    car: str
    subsystem: str
    channel: str
    value: TelemetryValue
    units: str
    source_file: str | None = None


class Normalizer(Protocol):
    """
    Protocol implemented by telemetry normalizers.
    """

    def normalize_packet(self, packet: ParsedPacket) -> list[TelemetryRecord]:
        """
        Convert one decoded parser packet into one or more telemetry records.
        """
        ...