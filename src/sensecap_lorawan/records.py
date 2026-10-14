"""Seven-byte records used by Gen1, S2101–S2106, and A1101."""

from .payload import DecodedPayload, Measurement, version


def decode_records(data: bytes) -> DecodedPayload:
    """Decode all channels and measurement IDs; retain unknown record metadata.

    The final two bytes are a trailer. Like Seeed's decoder, this function
    does not validate a CRC.
    """
    if len(data) < 9 or (len(data) - 2) % 7:
        raise ValueError("Invalid SenseCAP frame length")
    result = DecodedPayload()
    sensor_ids: dict[int, dict[int, bytes]] = {}
    for offset in range(0, len(data) - 2, 7):
        channel = data[offset]
        identifier = int.from_bytes(data[offset + 1 : offset + 3], "little")
        raw = data[offset + 3 : offset + 7]
        if identifier > 4096:
            value = int.from_bytes(raw, "little", signed=True) / 1000
            result.measurements.append(
                Measurement(identifier, None if value >= 2_000_000 else value, channel)
            )
        elif identifier in (0, 1):
            prefix = "" if identifier == 0 else f"sensor_{channel}_"
            result.metadata[prefix + "hardware_version"] = version(raw[2:][::-1])
            result.metadata[prefix + "firmware_version"] = version(raw[:2][::-1])
        elif identifier in (2, 3):
            sensor_ids.setdefault(channel, {})[identifier] = raw[::-1]
        elif identifier == 7:
            result.metadata["battery_percentage"] = int.from_bytes(raw[:2], "little")
            result.metadata["measurement_interval"] = (
                int.from_bytes(raw[2:], "little") * 60
            )
        elif identifier == 9:
            result.metadata.update(
                detection_type=raw[3], model_id=raw[2], model_version=raw[1]
            )
        elif identifier == 0x120:
            result.metadata[f"sensor_{channel}_removed"] = True
        elif identifier not in (4, 5, 6):
            result.metadata[f"record_{channel}_{identifier}"] = raw.hex()
    for channel, parts in sensor_ids.items():
        if 2 in parts and 3 in parts:
            result.metadata[f"sensor_{channel}_id"] = (parts[3] + parts[2]).hex()
    return result
