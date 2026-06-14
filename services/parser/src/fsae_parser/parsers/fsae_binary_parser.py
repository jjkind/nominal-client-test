"""
Purpose:
Decodes the synthetic Formula SAE binary telemetry file format.

This parser reads the binary session header and interleaved channel packets,
then converts each binary packet into a ParsedPacket object. It does not
normalize field names or prepare data for a specific backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Iterator

from fsae_parser.models import ParsedPacket


HEADER_FORMAT = "<4sHHIQHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

PACKET_HEADER_FORMAT = "<IHH"
PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)


@dataclass(frozen=True)
class ChannelDefinition:
    channel_id: int
    name: str
    payload_format: str
    fields: tuple[str, ...]
    units: dict[str, str]


CHANNELS: dict[int, ChannelDefinition] = {
    1: ChannelDefinition(
        channel_id=1,
        name="battery",
        payload_format="<ffffHBB",
        fields=(
            "pack_voltage_v",
            "pack_current_a",
            "soc_pct",
            "max_cell_temp_c",
            "min_cell_mv",
            "contactor_state",
            "fault_flags",
        ),
        units={
            "pack_voltage_v": "V",
            "pack_current_a": "A",
            "soc_pct": "%",
            "max_cell_temp_c": "degC",
            "min_cell_mv": "mV",
            "contactor_state": "enum",
            "fault_flags": "bitfield",
        },
    ),
    2: ChannelDefinition(
        channel_id=2,
        name="motor",
        payload_format="<ffffHH",
        fields=(
            "motor_rpm",
            "torque_cmd_nm",
            "torque_actual_nm",
            "inverter_temp_c",
            "dc_bus_v",
            "fault_flags",
        ),
        units={
            "motor_rpm": "rpm",
            "torque_cmd_nm": "Nm",
            "torque_actual_nm": "Nm",
            "inverter_temp_c": "degC",
            "dc_bus_v": "V",
            "fault_flags": "bitfield",
        },
    ),
    3: ChannelDefinition(
        channel_id=3,
        name="pedals",
        payload_format="<fffBB",
        fields=(
            "accel_pedal_pct",
            "brake_front_psi",
            "brake_rear_psi",
            "drive_mode",
            "plausibility_fault",
        ),
        units={
            "accel_pedal_pct": "%",
            "brake_front_psi": "psi",
            "brake_rear_psi": "psi",
            "drive_mode": "enum",
            "plausibility_fault": "bool",
        },
    ),
    4: ChannelDefinition(
        channel_id=4,
        name="vehicle_dynamics",
        payload_format="<fffffff",
        fields=(
            "vehicle_speed_mps",
            "steering_deg",
            "yaw_rate_dps",
            "lat_g",
            "long_g",
            "wheel_fl_mps",
            "wheel_fr_mps",
        ),
        units={
            "vehicle_speed_mps": "m/s",
            "steering_deg": "deg",
            "yaw_rate_dps": "deg/s",
            "lat_g": "g",
            "long_g": "g",
            "wheel_fl_mps": "m/s",
            "wheel_fr_mps": "m/s",
        },
    ),
}


class FsaeBinaryParser:
    """
    Parser for the synthetic Formula SAE binary session format.

    Produces ParsedPacket objects. The normalizer is responsible for turning
    these packets into one-record-per-telemetry-value output.
    """

    def parse_file(self, path: Path) -> Iterator[ParsedPacket]:
        with path.open("rb") as file:
            header_bytes = file.read(HEADER_SIZE)

            if len(header_bytes) != HEADER_SIZE:
                raise ValueError(f"{path.name} is too small to contain a valid header.")

            (
                magic,
                version,
                header_size,
                session_id,
                session_start_unix_ms,
                channel_count,
                reserved,
            ) = struct.unpack(HEADER_FORMAT, header_bytes)

            if magic != b"FSAE":
                raise ValueError(f"{path.name} has invalid magic: {magic!r}")

            if version != 1:
                raise ValueError(f"{path.name} has unsupported version: {version}")

            if header_size != HEADER_SIZE:
                raise ValueError(
                    f"{path.name} has unexpected header size: {header_size}"
                )

            while True:
                packet_header = file.read(PACKET_HEADER_SIZE)

                if not packet_header:
                    break

                if len(packet_header) != PACKET_HEADER_SIZE:
                    raise ValueError(
                        f"{path.name} ended in the middle of a packet header."
                    )

                timestamp_ms, channel_id, payload_len = struct.unpack(
                    PACKET_HEADER_FORMAT,
                    packet_header,
                )

                payload = file.read(payload_len)

                if len(payload) != payload_len:
                    raise ValueError(
                        f"{path.name} ended in the middle of a packet payload."
                    )

                channel = CHANNELS.get(channel_id)

                if channel is None:
                    raise ValueError(f"Unknown channel_id={channel_id}")

                expected_payload_len = struct.calcsize(channel.payload_format)

                if payload_len != expected_payload_len:
                    raise ValueError(
                        f"channel_id={channel_id} expected payload length "
                        f"{expected_payload_len}, got {payload_len}"
                    )

                unpacked_values = struct.unpack(channel.payload_format, payload)

                values = dict(zip(channel.fields, unpacked_values, strict=True))

                yield ParsedPacket(
                    session_id=str(session_id),
                    session_start_unix_ms=session_start_unix_ms,
                    timestamp_ms=timestamp_ms,
                    channel_id=channel_id,
                    subsystem=channel.name,
                    values=values,
                    units=channel.units,
                    source_file=path.name,
                )