"""
Purpose:
Writes normalized telemetry records to parser output formats.

Supported output formats:
- jsonl: narrow JSONL records for Loki-style log ingestion.
- parquet: wide Parquet table for analytics/Nominal-style workflows.
- dataframe: wide CSV file that is easy to inspect and can be loaded into pandas.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from fsae_parser.models import TelemetryRecord


class TelemetryOutputWriter:
    def write(
        self,
        records: Iterable[TelemetryRecord],
        output_format: str,
        temp_path: Path,
        final_path: Path,
    ) -> int:
        if output_format == "jsonl":
            return self.write_jsonl(
                records=records,
                temp_path=temp_path,
                final_path=final_path,
            )

        if output_format == "parquet":
            return self.write_wide_parquet(
                records=records,
                temp_path=temp_path,
                final_path=final_path,
            )

        if output_format == "dataframe":
            return self.write_wide_csv(
                records=records,
                temp_path=temp_path,
                final_path=final_path,
            )

        raise ValueError(
            f"Unsupported output_format={output_format!r}. "
            "Valid choices are: jsonl, parquet, dataframe."
        )

    @staticmethod
    def write_jsonl(
        records: Iterable[TelemetryRecord],
        temp_path: Path,
        final_path: Path,
    ) -> int:
        count = 0

        with temp_path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")
                count += 1

        temp_path.rename(final_path)
        return count

    def write_wide_csv(
        self,
        records: Iterable[TelemetryRecord],
        temp_path: Path,
        final_path: Path,
    ) -> int:
        df = self.records_to_wide_dataframe(records)
        df.to_csv(temp_path, index=False)
        temp_path.rename(final_path)
        return len(df)

    def write_wide_parquet(
        self,
        records: Iterable[TelemetryRecord],
        temp_path: Path,
        final_path: Path,
    ) -> int:
        df = self.records_to_wide_dataframe(records)
        df.to_parquet(temp_path, index=False)
        temp_path.rename(final_path)
        return len(df)

    @staticmethod
    def records_to_wide_dataframe(records: Iterable[TelemetryRecord]) -> pd.DataFrame:
        materialized_records = list(records)

        if not materialized_records:
            return pd.DataFrame(
                columns=[
                    "timestamp_ns",
                    "timestamp_iso",
                    "session_id",
                    "car",
                    "source_file",
                ]
            )

        channel_names_by_key: dict[tuple[str, str], str] = {}
        channel_counts: dict[str, int] = {}

        for record in materialized_records:
            key = (record.subsystem, record.channel)

            if key not in channel_names_by_key:
                channel_names_by_key[key] = record.channel
                channel_counts[record.channel] = channel_counts.get(record.channel, 0) + 1

        duplicated_channel_names = {
            channel
            for channel, count in channel_counts.items()
            if count > 1
        }

        column_name_by_key = {
            key: (
                f"{key[0]}_{channel_name}"
                if channel_name in duplicated_channel_names
                else channel_name
            )
            for key, channel_name in channel_names_by_key.items()
        }

        rows_by_timestamp: dict[int, dict[str, object]] = {}

        for record in materialized_records:
            row = rows_by_timestamp.setdefault(
                record.timestamp_ns,
                {
                    "timestamp_ns": record.timestamp_ns,
                    "timestamp_iso": record.timestamp_iso,
                    "session_id": record.session_id,
                    "car": record.car,
                    "source_file": record.source_file,
                },
            )

            column_name = column_name_by_key[(record.subsystem, record.channel)]
            row[column_name] = record.value

        df = pd.DataFrame(rows_by_timestamp.values())
        df = df.sort_values("timestamp_ns").reset_index(drop=True)

        metadata_columns = [
            "timestamp_ns",
            "timestamp_iso",
            "session_id",
            "car",
            "source_file",
        ]
        signal_columns = sorted(
            column
            for column in df.columns
            if column not in metadata_columns
        )

        return df[metadata_columns + signal_columns]