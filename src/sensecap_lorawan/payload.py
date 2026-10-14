"""Decoded measurements shared by the SenseCAP wire protocols."""

from dataclasses import dataclass, field
from datetime import datetime

type Value = None | bool | int | float | str | list[Value] | dict[str, Value]


@dataclass(frozen=True)
class Measurement:
    """A vendor measurement ID, channel, and optional device collection time."""

    id: int
    value: Value
    channel: int = 1
    timestamp: datetime | None = None
    attributes: dict[str, Value] = field(default_factory=dict)


@dataclass
class DecodedPayload:
    """Measurements and device metadata from one complete uplink."""

    measurements: list[Measurement] = field(default_factory=list)
    metadata: dict[str, Value] = field(default_factory=dict)


def number(data: bytes, divisor: float = 1, *, nullable: bool = False) -> float | None:
    """Read a signed big-endian sensor value, including the absent sentinel."""
    if nullable and data == b"\x80" + bytes(len(data) - 1):
        return None
    return int.from_bytes(data, "big", signed=True) / divisor


def version(data: bytes) -> str:
    """Read a major/minor version."""
    return ".".join(str(part) for part in data)
