"""
Purpose:
Exposes parser implementations from the parsers package.

For now, this package exposes FsaeBinaryParser, which decodes the synthetic
Formula SAE binary session format into ParsedPacket objects.
"""

from .fsae_binary_parser import FsaeBinaryParser

__all__ = ["FsaeBinaryParser"]