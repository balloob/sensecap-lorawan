"""SenseCAP models and official ChirpStack/TTS catalog identities."""

from typing import ClassVar

from .device import DecoderProtocol, SenseCapDevice

VENDOR_ID = 0x02E8


class S2100(SenseCapDevice):
    """Data logger with numbered input channels."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "b7da14c7-d5de-49a1-8937-5063719bf70e"),
        "tts": ("sensecap", "sensecaps2100-data-logger"),
    }
    _protocol: ClassVar[DecoderProtocol] = "blocks"
    _ports = (3,)


class S2101(SenseCapDevice):
    """Air temperature and relative humidity."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "fc455aa2-01cf-492b-9359-a5d8c9a0e1b3"),
        "tts": ("sensecap", "sensecaps2101-temp-humid"),
    }
    _ranges = {4097: (-40, 85), 4098: (0, 100)}

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def humidity(self) -> float | None:
        """Relative humidity in percent."""
        return self._number(4098)


class S2102(SenseCapDevice):
    """Light intensity in lux."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "92e11305-8190-41cc-84d0-ddc452cf1889"),
        "tts": ("sensecap", "sensecaps2102-light"),
    }
    _ranges = {4099: (0, 160_000)}

    @property
    def illuminance(self) -> float | None:
        """Light intensity in lux."""
        return self._number(4099)


class S2103(SenseCapDevice):
    """Air temperature, relative humidity, and carbon dioxide."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "3b46865c-036d-4f0b-8e39-cbb31aa091b4"),
        "tts": ("sensecap", "sensecaps2103-co2-temp-humid"),
    }

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def humidity(self) -> float | None:
        """Relative humidity in percent."""
        return self._number(4098)

    @property
    def co2(self) -> float | None:
        """Carbon dioxide concentration in ppm."""
        return self._number(4100)


class S2104(SenseCapDevice):
    """Soil temperature and volumetric water content."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "b941a068-8494-4a17-ac21-b0a083787e72"),
        "tts": ("sensecap", "sensecaps2104-soil-moisture-temp"),
    }

    @property
    def soil_temperature(self) -> float | None:
        """Soil temperature in degrees Celsius."""
        return self._number(4102)

    @property
    def soil_moisture(self) -> float | None:
        """Volumetric soil water content in percent."""
        return self._number(4103)


class S2105(S2104):
    """Soil temperature, moisture, and electrical conductivity."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "5cc452c5-03e6-43af-9525-f0f05767a661"),
        "tts": ("sensecap", "sensecaps2105-soll-moisture-temp-ec"),
    }

    @property
    def conductivity(self) -> float | None:
        """Soil electrical conductivity in dS/m."""
        return self._number(4108)


class S2106(SenseCapDevice):
    """Temperature and pH."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "c8e601fc-6015-46f9-be5d-abb0e2863b96"),
    }

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def ph(self) -> float | None:
        """Measured pH."""
        return self._number(4106)


class S2107(SenseCapDevice):
    """Three temperature probes, including buffered readings."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "7e5c3173-627a-4c89-abf2-ffb2562c720c"),
    }
    _protocol: ClassVar[DecoderProtocol] = "blocks"
    _ports = (3,)

    def temperature(self, channel: int = 1) -> float | None:
        """Temperature in degrees Celsius for probe 1, 2, or 3."""
        return self._number(4203, channel)


class S2120(SenseCapDevice):
    """Weather station measurements."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "ba6c2e5d-d894-41d1-a5c1-5e8f4a7d3826"),
        "tts": ("sensecap", "sensecaps2120-8-in-1"),
    }
    _protocol: ClassVar[DecoderProtocol] = "blocks"
    _ports = (3,)

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def humidity(self) -> float | None:
        """Relative humidity in percent."""
        return self._number(4098)

    @property
    def illuminance(self) -> float | None:
        """Light intensity in lux."""
        return self._number(4099)

    @property
    def uv_index(self) -> float | None:
        """Dimensionless UV index."""
        return self._number(4190)

    @property
    def wind_speed(self) -> float | None:
        """Wind speed in m/s."""
        return self._number(4105)

    @property
    def wind_direction(self) -> float | None:
        """Wind direction in degrees."""
        return self._number(4104)

    @property
    def rainfall(self) -> float | None:
        """Rainfall intensity in mm/h."""
        return self._number(4113)

    @property
    def pressure(self) -> float | None:
        """Barometric pressure in Pa."""
        return self._number(4101)

    @property
    def wind_gust(self) -> float | None:
        """Peak wind gust in m/s."""
        return self._number(4191)

    @property
    def rain_accumulation(self) -> float | None:
        """Accumulated rainfall in mm."""
        return self._number(4213)


class A1101(SenseCapDevice):
    """Vision AI measurement records."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "38630583-7d56-4376-9bc4-cd3ee97f460d"),
    }


class A1102(SenseCapDevice):
    """Vision AI detections and digital meter readings."""

    identifiers = {}
    _protocol: ClassVar[DecoderProtocol] = "vision"
    _ports = (3,)


class T1000(SenseCapDevice):
    """T1000 A/B tracker measurements and scan results."""

    identifiers = {
        "tts": ("sensecap", "sensecapt1000-tracker-ab"),
    }
    _protocol: ClassVar[DecoderProtocol] = "t1000"
    _ports = (5,)

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def light(self) -> float | None:
        """Tracker light reading."""
        return self._number(4199)

    @property
    def longitude(self) -> float | None:
        """Longitude in degrees."""
        return self._number(4197)

    @property
    def latitude(self) -> float | None:
        """Latitude in degrees."""
        return self._number(4198)


class T1000A(T1000):
    """ChirpStack T1000-A catalog identity."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "a801aa3f-58d8-4e6f-80b9-34fb1d26910f"),
    }


class T1000B(T1000):
    """ChirpStack T1000-B catalog identity."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "9acef00b-7893-4211-9bca-e03fb9f51327"),
    }


class T1000E(T1000):
    """T1000-E running SenseCAP LoRaWAN firmware."""

    identifiers = {}
    _protocol: ClassVar[DecoderProtocol] = "t1000e"
    _ports = (5,)


class T2000(SenseCapDevice):
    """T2000 A/B/C tracker measurements."""

    identifiers = {
        "chirpstack": (VENDOR_ID, "dc48d269-c13c-4d63-b135-0e3881d543a8"),
        "tts": ("sensecap", "sensecapt2000-tracker-abc"),
    }
    _protocol: ClassVar[DecoderProtocol] = "t2000"
    _ports = (5,)

    @property
    def longitude(self) -> float | None:
        """Longitude in degrees."""
        return self._number(4197)

    @property
    def latitude(self) -> float | None:
        """Latitude in degrees."""
        return self._number(4198)


class WM1110(SenseCapDevice):
    """WM1110 LoRaWAN tracker and custom sensor frames."""

    identifiers = {}
    _protocol: ClassVar[DecoderProtocol] = "wm1110"
    _ports = (5,)


class Gen1AirTemperatureHumidity(SenseCapDevice):
    """First-generation air temperature and humidity sensor."""

    identifiers = {
        "tts": ("sensecap", "sensecap-air-th"),
    }

    @property
    def temperature(self) -> float | None:
        """Temperature in degrees Celsius."""
        return self._number(4097)

    @property
    def humidity(self) -> float | None:
        """Relative humidity in percent."""
        return self._number(4098)


class Gen1CO2(SenseCapDevice):
    """First-generation carbon dioxide sensor."""

    identifiers = {
        "tts": ("sensecap", "sensecap-co2"),
    }

    @property
    def co2(self) -> float | None:
        """Carbon dioxide concentration in ppm."""
        return self._number(4100)


class Gen1Light(SenseCapDevice):
    """First-generation light sensor."""

    identifiers = {
        "tts": ("sensecap", "sensecap-light"),
    }

    @property
    def illuminance(self) -> float | None:
        """Light intensity in lux."""
        return self._number(4099)


class Gen1Pressure(SenseCapDevice):
    """First-generation barometric pressure sensor."""

    identifiers = {
        "tts": ("sensecap", "sensecap-pressure"),
    }

    @property
    def pressure(self) -> float | None:
        """Barometric pressure in Pa."""
        return self._number(4101)


class Gen1SoilTemperatureMoisture(SenseCapDevice):
    """First-generation soil temperature and moisture sensor."""

    identifiers = {
        "tts": ("sensecap", "sensecap-soil-th"),
    }

    @property
    def soil_temperature(self) -> float | None:
        """Soil temperature in degrees Celsius."""
        return self._number(4102)

    @property
    def soil_moisture(self) -> float | None:
        """Volumetric soil water content in percent."""
        return self._number(4103)
