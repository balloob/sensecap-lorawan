"""Variable record formats for S2100, S2107, S2120, and A1102."""

from datetime import UTC, datetime

from .payload import DecodedPayload, Measurement, number, version

_LENGTHS = {
    **dict.fromkeys(
        (
            0x01,
            0x20,
            0x21,
            0x30,
            0x31,
            0x33,
            0x40,
            0x41,
            0x42,
            0x43,
            0x44,
            0x45,
            0x46,
            0x48,
            0x4A,
        ),
        10,
    ),
    0x02: 8,
    0x4B: 8,
    0x03: 1,
    0x06: 1,
    0x05: 4,
    0x34: 4,
    **dict.fromkeys((0x04, 0x10, 0x32, 0x35, 0x36, 0x37, 0x38, 0x39), 9),
    0x47: 6,
    0x49: 7,
    0x4C: 6,
    0x7F: 1,
}


def decode_blocks(data: bytes, *, vision: bool = False) -> DecodedPayload:
    """Decode a complete uplink, rejecting unknown or truncated record layouts."""
    if not data:
        raise ValueError("Empty SenseCAP payload")
    frames: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(data):
        identifier = data[offset]
        length = _LENGTHS.get(identifier)
        if length is None or offset + length + 1 > len(data):
            raise ValueError(f"Unknown or truncated SenseCAP record: {identifier:#x}")
        frames.append((identifier, data[offset + 1 : offset + 1 + length]))
        offset += length + 1
    result = DecodedPayload()
    model_id = None
    if vision:
        for identifier, raw in frames:
            if identifier == 0x33:
                model_id = (
                    int(int.from_bytes(raw[6:10], "big", signed=True) / 1000)
                    - 1_000_000
                )
                result.metadata["model_id"] = model_id
    for identifier, raw in frames:
        values: list[tuple[int, int, int, float]] = []
        if identifier in (0x01, 0x4A):
            values = [
                (4097, 0, 2, 10),
                (4098, 2, 3, 1),
                (4099, 3, 7, 1),
                (4190, 7, 8, 10),
                (4105, 8, 10, 10),
            ]
        elif identifier in (0x02, 0x4B):
            values = [(4104, 0, 2, 1), (4113, 2, 6, 1000), (4101, 6, 8, 0.1)]
        elif identifier == 0x4C:
            values = [(4191, 0, 2, 10), (4213, 2, 6, 1000)]
        elif identifier == 0x03:
            result.metadata["battery_percentage"] = raw[0]
        elif identifier in (0x04, 0x39, 0x49):
            result.metadata.update(
                battery_percentage=raw[0],
                hardware_version=version(raw[1:3]),
                firmware_version=version(raw[3:5]),
                measurement_interval=int.from_bytes(raw[5:7], "big") * 60,
            )
            if identifier != 0x49:
                key = (
                    "threshold_measurement_interval"
                    if identifier == 0x39
                    else "gps_interval"
                )
                result.metadata[key] = int.from_bytes(raw[7:9], "big") * (
                    1 if identifier == 0x39 else 60
                )
        elif identifier == 0x05:
            result.metadata.update(
                measurement_interval=int.from_bytes(raw[:2], "big") * 60,
                gps_interval=int.from_bytes(raw[2:], "big") * 60,
            )
        elif identifier == 0x06:
            result.metadata["sensor_error"] = raw[0]
        elif identifier == 0x10:
            result.metadata[f"sensor_{raw[0] >> 4}"] = {
                "status": (raw[0] >> 3) & 1,
                "type": raw[0] & 7,
                "eui": raw[1:].hex(),
            }
        elif identifier in (0x20, 0x21, 0x43, 0x44, 0x45):
            first = 4180 if identifier in (0x21, 0x45) else 4175
            for i in range(5):
                result.measurements.append(
                    Measurement(
                        first + i,
                        f"{int.from_bytes(raw[i * 2 : i * 2 + 1], signed=True)}."
                        f"{int.from_bytes(raw[i * 2 + 1 : i * 2 + 2], signed=True)}",
                    )
                )
        elif identifier in (0x30, 0x31, 0x32, 0x33):
            channels = (raw[0] >> 4, raw[0] & 15)
            start = 1 if identifier == 0x32 else 2
            for i, channel in enumerate(channels):
                value = number(raw[start + i * 4 : start + (i + 1) * 4], 1000)
                if vision:
                    if value == -1:
                        continue
                    measurement_id = (
                        4165 + i if identifier in (0x30, 0x31) else 4164 + channel
                    )
                    if identifier == 0x33 and i == 1:
                        if channel == 10:
                            result.measurements.append(
                                Measurement(
                                    measurement_id,
                                    {
                                        60086: "Person Detection--Swift YOLO",
                                        60113: "Digital Meter Electricity",
                                        60242: "Person Detection",
                                    }.get(model_id or 0, "unknown model"),
                                )
                            )
                        continue
                    assert value is not None
                    result.measurements.append(
                        Measurement(
                            measurement_id, value + (0 if model_id == 60113 else 0.01)
                        )
                    )
                elif channel:
                    result.measurements.append(Measurement(channel, value))
        elif identifier == 0x34:
            result.metadata.update(
                dict(
                    zip(
                        (
                            "datalogger_protocol",
                            "gpio_input",
                            "analog_type",
                            "analog_interface",
                        ),
                        raw,
                        strict=True,
                    )
                )
            )
        elif identifier in (0x35, 0x36, 0x37, 0x38):
            first = 3920 + ((raw[0] >> 4) - 1) * 2
            values = [(first, 1, 5, 1000), (first + 1, 5, 9, 1000)]
        elif identifier in (0x40, 0x41):
            values = [
                (4193, 0, 2, 1),
                (4192, 2, 4, 1),
                (4150, 4, 6, 100),
                (4151, 6, 8, 100),
                (4152, 8, 10, 100),
            ]
        elif identifier == 0x42:
            values = [
                (4097, 0, 2, 100),
                (4098, 2, 4, 100),
                (4195, 4, 6, 1),
                (4100, 6, 8, 1),
                (4196, 8, 10, 1),
            ]
        elif identifier in (0x46, 0x47):
            timestamp = (
                datetime.fromtimestamp(int.from_bytes(raw[:4], "big"), UTC)
                if identifier == 0x46
                else None
            )
            start = 4 if identifier == 0x46 else 0
            for i in range(3):
                result.measurements.append(
                    Measurement(
                        4203,
                        number(
                            raw[start + i * 2 : start + i * 2 + 2], 100, nullable=True
                        ),
                        i + 1,
                        timestamp,
                    )
                )
        elif identifier == 0x48:
            result.metadata["channel_status"] = {
                str(i + 1): value for i, value in enumerate(raw) if value != 255
            }
        for measurement_id, start, end, divisor in values:
            value = (
                int.from_bytes(raw[start:end], "big") / divisor
                if identifier in (0x01, 0x02, 0x4A, 0x4B, 0x4C)
                and measurement_id != 4097
                else number(raw[start:end], divisor)
            )
            result.measurements.append(Measurement(measurement_id, value))
    return result
