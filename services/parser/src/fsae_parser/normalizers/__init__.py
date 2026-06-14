"""
Purpose:
Exposes normalizer implementations from the normalizers package.

Normalizers convert decoded parser packets into backend-neutral telemetry
records that can later be exported to Loki, Nominal, Elasticsearch, or another
system.
"""

from .telemetry_normalizer import TelemetryNormalizer

__all__ = ["TelemetryNormalizer"]