"""T1000 A/B/E, T2000, and WM1110 uplink protocols."""

from datetime import UTC, datetime
from typing import Literal

from .payload import DecodedPayload, Measurement, Value, number, version

type TrackerProtocol = Literal["t1000", "t1000e", "t2000", "wm1110"]

_LENGTHS = {
    "t1000": {
        1: 46,
        2: 15,
        3: 31,
        4: 9,
        5: 4,
        6: 21,
        7: 41,
        8: 34,
        9: 17,
        10: 37,
        11: 30,
        12: 0,
        13: 4,
        15: 16,
        16: 12,
        17: 13,
        26: 27,
        27: 47,
        28: 40,
        29: 19,
    },
    "t1000e": {0x1E: 12, 0x1F: 20, 0x22: 14, 0x25: 12, 0x26: 6},
    "t2000": {
        0x0C: 0,
        0x0D: 4,
        0x27: 45,
        0x28: 29,
        0x29: 11,
        0x2A: 5,
        0x2B: 22,
        0x2E: 16,
        0x31: 14,
        0x32: 8,
    },
    "wm1110": {0x13: 11, 0x14: 36, 0x15: 29, 0x16: 8, 0x18: 27},
}


def _scans(raw: bytes) -> list[Value]:
    return [
        {
            "mac": raw[i : i + 6].hex(":"),
            "rssi": int.from_bytes(raw[i + 6 : i + 7], "big", signed=True),
        }
        for i in range(0, len(raw), 7)
        if raw[i : i + 6] != b"\xff" * 6
    ]


def _events(raw: bytes, limit: int = 8) -> list[Value]:
    bits = int.from_bytes(raw, "big")
    return [i + 1 for i in range(min(len(raw) * 8, limit)) if bits & (1 << i)]


def decode_tracker(data: bytes, protocol: TrackerProtocol = "t1000") -> DecodedPayload:
    """Decode complete tracker frames without resolving scans into coordinates."""
    if not data:
        raise ValueError("Empty SenseCAP tracker payload")
    result = DecodedPayload()
    offset = 0
    while offset < len(data):
        identifier = data[offset]
        remaining = data[offset:]
        length = _LENGTHS[protocol].get(identifier)
        skip = 1
        fragment = (protocol == "t1000" and identifier == 0x0E) or (
            protocol == "wm1110" and identifier == 0x12
        )
        if fragment:
            if len(remaining) < 5:
                raise ValueError("Truncated GNSS fragment")
            length = 4 + remaining[4]
        elif protocol == "wm1110" and identifier == 0x17:
            if (
                len(remaining) < 2
                or not 13 <= remaining[1] <= 49
                or (remaining[1] - 9) % 4
            ):
                raise ValueError("Invalid WM1110 custom frame length")
            length, skip = remaining[1] - 1, 2
        else:
            count_offset = None
            if protocol == "t1000e":
                count_offset = {0x20: 13, 0x21: 13, 0x23: 7, 0x24: 7}.get(identifier)
            elif protocol == "t2000":
                count_offset = {0x2C: 15, 0x2D: 15, 0x2F: 9, 0x30: 9}.get(identifier)
            if count_offset is not None:
                if len(remaining) <= count_offset:
                    raise ValueError("Truncated tracker scan header")
                length = count_offset + remaining[count_offset] * 7
        if length is None or len(remaining) < length + 1:
            raise ValueError(f"Unknown or truncated tracker frame: {identifier:#x}")
        raw = remaining[skip : length + 1]
        if fragment:
            raw = raw[:3] + raw[4:]
        _decode_frame(result, identifier, raw, protocol)
        offset += length + 1
    return result


def _decode_frame(
    result: DecodedPayload, identifier: int, raw: bytes, protocol: TrackerProtocol
) -> None:
    timestamp: datetime | None = None
    attributes: dict[str, Value] = {}

    def add(measurement_id: int, value: Value) -> None:
        result.measurements.append(
            Measurement(
                measurement_id, value, timestamp=timestamp, attributes=dict(attributes)
            )
        )

    def fields(spec: list[tuple[int, int, int, float]]) -> None:
        for measurement_id, start, end, divisor in spec:
            add(measurement_id, number(raw[start:end], divisor, nullable=True))

    def uint(measurement_id: int, start: int, end: int) -> None:
        add(measurement_id, int.from_bytes(raw[start:end], "big"))

    def time_at(start: int) -> None:
        nonlocal timestamp
        timestamp = datetime.fromtimestamp(
            int.from_bytes(raw[start : start + 4], "big"), UTC
        )

    def shard(start: int) -> None:
        attributes.update(
            count=raw[start] >> 4,
            index=raw[start] & 15,
            group_id=int.from_bytes(raw[start + 1 : start + 3], "big"),
        )

    def config(start: int, *, sensors: bool) -> None:
        spec = [
            (3946, start, start + 1, 1),
            (3947, start + 1, start + 3, 1),
            (3948, start + 3, start + 5, 1),
            (3949, start + 5, start + 6, 1),
            (3950, start + 6, start + 8, 1),
            (3951, start + 8, start + 9, 1),
            (3952, start + 9, start + 11, 1),
        ]
        if sensors:
            for base, pos in ((3953, start + 11), (3959, start + 21)):
                spec.extend(
                    [
                        (base, pos, pos + 1, 1),
                        (base + 1, pos + 1, pos + 3, 1),
                        (base + 2, pos + 3, pos + 5, 1),
                        (base + 3, pos + 5, pos + 7, 10),
                        (base + 4, pos + 7, pos + 9, 10),
                        (base + 5, pos + 9, pos + 10, 1),
                    ]
                )
        # Only thresholds are signed; intervals and switches are unsigned.
        signed = {3947, 3956, 3957, 3962, 3963}
        for mid, start, end, divisor in spec:
            if mid in signed:
                add(mid, number(raw[start:end], divisor, nullable=True))
            else:
                uint(mid, start, end)

    def intervals(start: int, *, uplink: bool) -> None:
        uint(3940, start, start + 1)
        uint(3965, start + 1, start + 2)
        for i, mid in enumerate((3942, 3943, 3944)):
            uint(mid, start + 2 + i * 2, start + 4 + i * 2)
        if uplink:
            mode = raw[start]
            add(
                3900,
                int.from_bytes(raw[start + 2 + mode * 2 : start + 4 + mode * 2], "big")
                if mode <= 2
                else 0,
            )

    if identifier == 0x0C:
        result.metadata["time_sync_requested"] = True
        return
    if identifier == 0x0D:
        result.metadata["error_code"] = int.from_bytes(raw, "big")
        return
    if (protocol == "t1000" and identifier == 0x0E) or (
        protocol == "wm1110" and identifier == 0x12
    ):
        shard(0)
        add(6152, raw[3:].hex())
        return

    if protocol == "t1000":
        if identifier in (1, 2):
            uint(3000, 0, 1)
            add(3502, version(raw[1:3]))
            add(3001, version(raw[3:5]))
            intervals(5, uplink=False)
            uint(3945, 13, 14)
            uint(3941, 14, 15)
            if identifier == 1:
                config(15, sensors=True)
        elif identifier == 3:
            config(0, sensors=True)
        elif identifier == 4:
            intervals(0, uplink=True)
            # This frame omits positioning strategy in the reference decoder.
            result.measurements[:] = [
                item for item in result.measurements if item.id != 3965
            ]
            uint(3941, 8, 9)
        elif identifier == 5:
            for i, mid in enumerate((3000, 3940, 3965, 3941)):
                uint(mid, i, i + 1)
        elif identifier in (6, 7, 8, 9, 10, 11, 26, 27, 28):
            time_at(4)
            attributes["motion_id"] = raw[3]
            add(4200, _events(raw[:3]))
            position = 8
            if identifier in (6, 9, 26):
                fields([(4197, 8, 12, 1_000_000), (4198, 12, 16, 1_000_000)])
                position = 16
            else:
                wifi = identifier in (7, 10, 27)
                position += 28 if wifi else 21
                add(5001 if wifi else 5002, _scans(raw[8:position]))
            if identifier in (6, 7, 8, 26, 27, 28):
                fields(
                    [
                        (4097, position, position + 2, 10),
                        (4199, position + 2, position + 4, 1),
                    ]
                )
                position += 4
            if identifier in (26, 27, 28):
                fields(
                    [
                        (4210 + i, position + i * 2, position + i * 2 + 2, 1)
                        for i in range(3)
                    ]
                )
                position += 6
            uint(3000, position, position + 1)
        elif identifier in (15, 16):
            time_at(4)
            attributes["motion_id"] = raw[3]
            position = 12 if identifier == 15 else 8
            shard(position + 1)
            add(4200, _events(raw[:3]))
            if identifier == 15:
                fields([(4097, 8, 10, 10), (4199, 10, 12, 1)])
            uint(3000, position, position + 1)
        elif identifier in (17, 29):
            time_at(4)
            uint(3576, 0, 1)
            add(4200, _events(raw[1:4]))
            fields([(4097, 8, 10, 10), (4199, 10, 12, 1)])
            if identifier == 29:
                fields([(4210 + i, 12 + i * 2, 14 + i * 2, 1) for i in range(3)])
            uint(3000, len(raw) - 1, len(raw))
    elif protocol == "t1000e":
        if identifier == 0x1E:
            uint(3000, 0, 1)
            add(3502, version(raw[1:3]))
            add(3001, version(raw[3:5]))
            for mid, start, end in (
                (3965, 5, 6),
                (3900, 6, 8),
                (3974, 8, 9),
                (3941, 9, 10),
                (3972, 10, 11),
                (3973, 11, 12),
            ):
                uint(mid, start, end)
        else:
            add(5003, _events(raw[:1]))
            uint(3000, 1, 2)
            fields([(4097, 2, 4, 10), (4199, 4, 6, 1)])
            axes = identifier in (0x1F, 0x20, 0x21, 0x25)
            position = 12 if axes else 6
            if axes:
                fields([(4210 + i, 6 + i * 2, 8 + i * 2, 1) for i in range(3)])
            if identifier in (0x1F, 0x22):
                fields(
                    [
                        (4197, position, position + 4, 1_000_000),
                        (4198, position + 4, position + 8, 1_000_000),
                    ]
                )
            elif identifier in (0x20, 0x21, 0x23, 0x24):
                add(
                    5001 if identifier in (0x20, 0x23) else 5002,
                    _scans(raw[position + 1 :]),
                )
    elif protocol == "t2000":
        if identifier in (0x27, 0x28):
            start = 5 if identifier == 0x27 else 0
            if start:
                uint(3000, 0, 1)
                add(3502, version(raw[1:3]))
                add(3001, version(raw[3:5]))
            intervals(start, uplink=True)
            for i, mid in enumerate((3974, 3976, 3977)):
                uint(mid, start + 8 + i, start + 9 + i)
            position = 27 if start else 11
            uint(3978, position, position + 1)
            length = raw[position + 1]
            if length > 16:
                raise ValueError("Invalid tracker UUID filter length")
            add(3979, raw[position + 2 : position + 2 + length].hex())
            if start:
                config(16, sensors=False)
        elif identifier == 0x29:
            config(0, sensors=False)
        elif identifier == 0x2A:
            for i, mid in enumerate((3000, 3940, 3965, 3974, 3976)):
                uint(mid, i, i + 1)
        else:
            time_at(3)
            failed = identifier in (0x31, 0x32)
            if failed:
                uint(3576, 0, 1)
            else:
                attributes["motion_id"] = raw[2]
            add(4200, _events(raw[1:3] if failed else raw[:2], 9))
            axes = identifier in (0x2B, 0x2C, 0x2D, 0x31)
            position = 13 if axes else 7
            if axes:
                fields([(4210 + i, 7 + i * 2, 9 + i * 2, 1) for i in range(3)])
            if identifier in (0x2B, 0x2E):
                fields(
                    [
                        (4197, position, position + 4, 1_000_000),
                        (4198, position + 4, position + 8, 1_000_000),
                    ]
                )
                position += 8
            uint(3000, position, position + 1)
            if identifier in (0x2C, 0x2D, 0x2F, 0x30):
                add(
                    5001 if identifier in (0x2C, 0x2F) else 5002,
                    _scans(raw[position + 2 :]),
                )
    elif protocol == "wm1110":
        if identifier in (0x13, 0x14, 0x15, 0x16):
            time_at(4)
            if identifier == 0x16:
                uint(3576, 0, 1)
                add(4200, _events(raw[1:4]))
            else:
                attributes["motion_id"] = raw[3]
                if identifier == 0x13:
                    shard(8)
                add(4200, _events(raw[:3]))
                if identifier != 0x13:
                    add(5001 if identifier == 0x14 else 5002, _scans(raw[8:]))
        elif identifier == 0x17:
            time_at(3)
            event_status = int.from_bytes(raw[:3], "big")
            add(4208, None if event_status == 0x800000 else event_status)
            for i, start in enumerate(range(7, len(raw), 4)):
                value = int.from_bytes(raw[start : start + 4], "big")
                add(4165 + i, None if value == 0x80000000 else value)
        elif identifier == 0x18:
            time_at(3)
            add(4200, _events(raw[:3]))
            fields(
                [
                    (4097, 7, 9, 10),
                    (4150, 21, 23, 100),
                    (4151, 23, 25, 100),
                    (4152, 25, 27, 100),
                ]
            )
            for mid, start, end, divisor in (
                (4098, 9, 10, 1),
                (4101, 10, 13, 1),
                (4115, 13, 15, 1),
                (4190, 15, 17, 100),
                (4206, 17, 19, 1),
                (4207, 19, 21, 1),
            ):
                value = int.from_bytes(raw[start:end], "big")
                add(
                    mid,
                    None if value == 1 << ((end - start) * 8 - 1) else value / divisor,
                )
