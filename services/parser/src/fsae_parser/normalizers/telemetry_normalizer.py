"""
Purpose:
Converts ParsedPacket objects into normalized TelemetryRecord objects.

A ParsedPacket may contain several values from one subsystem snapshot. This
normalizer expands each packet into one record per telemetry channel value.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from fsae_parser.models import ParsedPacket, TelemetryRecord, TelemetryValue


CHANNEL_NAME_MAP = {
    # Battery
    "pack_voltage_v": "pack_voltage",
    "pack_current_a": "pack_current",
    "soc_pct": "soc",
    "max_cell_temp_c": "max_cell_temp",
    "min_cell_mv": "min_cell_voltage",
    "contactor_state": "contactor_state",
    "fault_flags": "fault_flags",

    # Motor
    "motor_rpm": "motor_rpm",
    "torque_cmd_nm": "torque_cmd",
    "torque_actual_nm": "torque_actual",
    "inverter_temp_c": "inverter_temp",
    "dc_bus_v": "dc_bus_voltage",

    # Pedals
    "accel_pedal_pct": "accel_pedal",
    "brake_front_psi": "brake_front_pressure",
    "brake_rear_psi": "brake_rear_pressure",
    "drive_mode": "drive_mode",
    "plausibility_fault": "plausibility_fault",

    # Vehicle dynamics
    "vehicle_speed_mps": "vehicle_speed",
    "steering_deg": "steering_angle",
    "yaw_rate_dps": "yaw_rate",
    "lat_g": "lateral_accel",
    "long_g": "longitudinal_accel",
    "wheel_fl_mps": "wheel_front_left_speed",
    "wheel_fr_mps": "wheel_front_right_speed",
}


class TelemetryNormalizer:
    """
    Converts parser-level ParsedPacket objects into normalized TelemetryRecord
    objects.

    A single packet can produce many telemetry records. For example, one battery
    packet becomes records for pack_voltage, pack_current, SOC, cell temp, etc.
    """

    def __init__(self, car: str = "fsae_demo") -> None:
        self.car = car

    def normalize_packet(self, packet: ParsedPacket) -> list[TelemetryRecord]:
        timestamp_ns = self._to_epoch_ns(
            session_start_unix_ms=packet.session_start_unix_ms,
            timestamp_ms=packet.timestamp_ms,
        )

        records: list[TelemetryRecord] = []

        for raw_channel, raw_value in packet.values.items():
            units = packet.units.get(raw_channel, "unknown")

            records.append(
                TelemetryRecord(
                    timestamp_ns=timestamp_ns,
                    session_id=packet.session_id,
                    car=self.car,
                    subsystem=packet.subsystem,
                    channel=self._normalize_channel_name(raw_channel),
                    value=self._normalize_value(raw_value, units),
                    units=units,
                    source_file=packet.source_file,
                )
            )

        return records

    def normalize_packets(
        self,
        packets: Iterable[ParsedPacket],
    ) -> Iterator[TelemetryRecord]:
        for packet in packets:
            yield from self.normalize_packet(packet)

    @staticmethod
    def _to_epoch_ns(session_start_unix_ms: int, timestamp_ms: int) -> int:
        return (session_start_unix_ms + timestamp_ms) * 1_000_000

    @staticmethod
    def _normalize_channel_name(raw_channel: str) -> str:
        return CHANNEL_NAME_MAP.get(raw_channel, raw_channel)

    @staticmethod
    def _normalize_value(value: TelemetryValue, units: str) -> TelemetryValue:
        if units == "bool":
            return bool(value)

        return value