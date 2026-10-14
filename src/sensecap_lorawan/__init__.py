"""SenseCAP device models for ChirpStack and The Things Stack."""

from lorawan_connection import DeviceCollection

from .device import SenseCapDevice
from .models import (
    A1101,
    A1102,
    S2100,
    S2101,
    S2102,
    S2103,
    S2104,
    S2105,
    S2106,
    S2107,
    S2120,
    T1000,
    T1000A,
    T1000B,
    T1000E,
    T2000,
    VENDOR_ID,
    WM1110,
    Gen1AirTemperatureHumidity,
    Gen1CO2,
    Gen1Light,
    Gen1Pressure,
    Gen1SoilTemperatureMoisture,
)
from .payload import DecodedPayload, Measurement
from .records import decode_records


def decode_s2101(data: bytes) -> dict[str, float | None]:
    """Decode S2101 channel-one temperature and humidity records."""
    result: dict[str, float | None] = {}
    for item in decode_records(data).measurements:
        key = {4097: "temperature", 4098: "humidity"}.get(item.id)
        if item.channel != 1 or key is None:
            continue
        value = item.value
        if value is not None:
            assert isinstance(value, (float, int))
            if key == "temperature" and not -40 <= value <= 85:
                raise ValueError("Temperature outside S2101 measurement range")
            if key == "humidity" and not 0 <= value <= 100:
                raise ValueError("Humidity outside valid range")
        result[key] = value
    return result


class SenseCapDeviceCollection(DeviceCollection[SenseCapDevice]):
    """Discover SenseCAP devices using official catalog identities."""

    DEVICES = (
        S2100,
        S2101,
        S2102,
        S2103,
        S2104,
        S2105,
        S2106,
        S2107,
        S2120,
        A1101,
        T1000,
        T1000A,
        T1000B,
        T2000,
        Gen1AirTemperatureHumidity,
        Gen1CO2,
        Gen1Light,
        Gen1Pressure,
        Gen1SoilTemperatureMoisture,
    )


__all__ = [
    "S2100",
    "S2101",
    "S2102",
    "S2103",
    "S2104",
    "S2105",
    "S2106",
    "S2107",
    "S2120",
    "A1101",
    "A1102",
    "T1000",
    "T1000A",
    "T1000B",
    "T1000E",
    "T2000",
    "WM1110",
    "Gen1AirTemperatureHumidity",
    "Gen1CO2",
    "Gen1Light",
    "Gen1Pressure",
    "Gen1SoilTemperatureMoisture",
    "VENDOR_ID",
    "DecodedPayload",
    "Measurement",
    "SenseCapDevice",
    "SenseCapDeviceCollection",
    "decode_s2101",
]
