"""Merge SenseCAP uplinks while preserving partial and out-of-order readings."""

from datetime import datetime
from typing import ClassVar, Literal, cast, override

from lorawan_connection import Device, DeviceDescriptor, DeviceEvent, EventType

from .blocks import decode_blocks
from .payload import DecodedPayload, Measurement, Value
from .records import decode_records
from .trackers import TrackerProtocol, decode_tracker

type DecoderProtocol = Literal["records", "blocks", "vision"] | TrackerProtocol


class SenseCapDevice(Device):
    """Latest measurements by channel and ID, plus vendor uplink metadata.

    Payload battery metadata is separate from Device.battery_level, which
    represents the standardized LoRaWAN status report.
    """

    _protocol: ClassVar[DecoderProtocol] = "records"
    _ports: ClassVar[tuple[int, ...]] = (1, 2)
    _ranges: ClassVar[dict[int, tuple[float, float]]] = {}

    def __init__(self, descriptor: DeviceDescriptor) -> None:
        super().__init__(descriptor)
        self.measurements: dict[int, dict[int, Measurement]] = {}
        self.metadata: dict[str, Value] = {}
        self._measurement_times: dict[tuple[int, int], datetime] = {}
        self._metadata_times: dict[str, datetime] = {}

    @classmethod
    def decode(cls, data: bytes) -> DecodedPayload:
        """Decode one complete payload; malformed frames raise ValueError."""
        if cls._protocol == "records":
            result = decode_records(data)
        elif cls._protocol in ("blocks", "vision"):
            result = decode_blocks(data, vision=cls._protocol == "vision")
        else:
            result = decode_tracker(data, cast(TrackerProtocol, cls._protocol))
        for item in result.measurements:
            if (
                item.channel == 1
                and item.id in cls._ranges
                and isinstance(item.value, (int, float))
            ):
                low, high = cls._ranges[item.id]
                if not low <= item.value <= high:
                    raise ValueError(
                        f"Measurement {item.id} outside {cls.__name__} range"
                    )
        return result

    def measurement_value(self, measurement_id: int, channel: int = 1) -> Value:
        """Read a measurement value, or None before it arrives or after a fault."""
        item = self.measurements.get(channel, {}).get(measurement_id)
        return item.value if item is not None else None

    def _number(self, measurement_id: int, channel: int = 1) -> float | None:
        value = self.measurement_value(measurement_id, channel)
        return float(value) if isinstance(value, (float, int)) else None

    @property
    def battery_percentage(self) -> float | None:
        """Battery percentage reported in the vendor uplink payload."""
        value = self.metadata.get("battery_percentage")
        return float(value) if isinstance(value, (int, float)) else self._number(3000)

    @override
    def handle_event(self, event: DeviceEvent) -> None:
        if (
            self.closed
            or event.type != EventType.UPLINK
            or event.f_port not in self._ports
        ):
            return
        try:
            payload = self.decode(event.data)
        except ValueError:
            return
        changed = False
        for item in payload.measurements:
            key = (item.channel, item.id)
            timestamp = item.timestamp or event.received_at
            if (
                key in self._measurement_times
                and timestamp < self._measurement_times[key]
            ):
                continue
            self._measurement_times[key] = timestamp
            self.measurements.setdefault(item.channel, {})[item.id] = item
            changed = True
        for name, value in payload.metadata.items():
            if (
                name in self._metadata_times
                and event.received_at < self._metadata_times[name]
            ):
                continue
            self.metadata[name] = value
            self._metadata_times[name] = event.received_at
            changed = True
        if changed:
            self.notify()
