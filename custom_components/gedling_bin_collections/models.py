"""Data models for Gedling Bin Collections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class BinCollection:
    """One collection date containing one or more services."""

    date: date
    services: tuple[str, ...]
    raw_services: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GedlingBinData:
    """Parsed data returned by the Gedling collection calendar."""

    address: str | None
    source_url: str
    collections: tuple[BinCollection, ...]
