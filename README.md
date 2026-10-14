# SenseCAP LoRaWAN

Read SenseCAP sensors through ChirpStack or The Things Stack using
[`lorawan-connection`](https://github.com/home-assistant-libs/lorawan-connection).

| Model | Readings | Automatic discovery |
| --- | --- | --- |
| S2100 | Data logger input channels | ChirpStack, TTS |
| S2101 | Air temperature, humidity | ChirpStack, TTS |
| S2102 | Light intensity | ChirpStack, TTS |
| S2103 | Air temperature, humidity, CO₂ | ChirpStack, TTS |
| S2104 | Soil temperature, moisture | ChirpStack, TTS |
| S2105 | Soil temperature, moisture, conductivity | ChirpStack, TTS |
| S2106 | Temperature, pH | ChirpStack |
| S2107 | Three temperature probes, including buffered readings | ChirpStack |
| S2120 | Temperature, humidity, light, UV, wind, pressure, rainfall | ChirpStack, TTS |
| A1101 | Vision AI measurements | ChirpStack |
| A1102 | Vision detections and digital meter readings | Explicit Python use |
| T1000 A/B | Position, temperature, light, motion, Wi-Fi/BLE scans | ChirpStack, TTS |
| T1000-E | Position, temperature, light, acceleration, Wi-Fi/BLE scans | Explicit Python use |
| T2000 A/B/C | Position, acceleration, motion, Wi-Fi/BLE scans | ChirpStack, TTS |
| WM1110 | GNSS fragments, Wi-Fi/BLE scans, environmental and custom readings | Explicit Python use |
| Gen1 sensors | Air temperature/humidity, CO₂, light, pressure, soil temperature/moisture | TTS |

Coverage follows every device family in Seeed's
[SenseCAP-Decoder](https://github.com/Seeed-Solution/SenseCAP-Decoder/tree/d0a234205fb9574dd03abd49561b60c243c0d1e3).
The A1102, T1000-E, and WM1110 classes have no automatic discovery identifiers:
they are absent from the SenseCAP catalogs checked for this release. Use their
`decode()` methods directly, or subclass them with your deployment's model identity.

Tracker support requires SenseCAP LoRaWAN firmware. Meshtastic firmware and
T1000 Mapper payloads are outside this decoder set. Wi-Fi/BLE scans and GNSS
fragments remain scan data; the library does not resolve them through a location
service or assemble fragmented GNSS messages. This library decodes uplinks and
does not implement device configuration commands.

Raw payloads are decoded locally; a server-side payload formatter is not required.

## Command-line reader

The `sensecap-lorawan` command lists devices or prints readings as they arrive.
Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to run it with
`uvx`, or use `pip install "sensecap-lorawan[chirpstack]"` for ChirpStack and
`pip install "sensecap-lorawan[tts]"` for The Things Stack.

### ChirpStack

Use a ChirpStack v4 gRPC endpoint, an API key, and the tenant UUID. The endpoint must
expose the gRPC API; forwarding only the web interface is not sufficient.

```sh
export CHIRPSTACK_API_KEY="your-api-key"
uvx --from "sensecap-lorawan[chirpstack]" sensecap-lorawan \
  --backend chirpstack \
  --server https://chirpstack.example.com:8080 \
  --tenant YOUR_TENANT_UUID \
  --application YOUR_APPLICATION_UUID
```

Repeat `--application` to select more applications. If omitted, all accessible
applications in the selected tenant are used. A global key can omit `--tenant`
to discover its accessible tenants.

### The Things Stack

Use the Application Server gRPC endpoint and an application API key with device
read and application traffic read rights. Specify each application explicitly.

```sh
export TTS_API_KEY="your-api-key"
uvx --from "sensecap-lorawan[tts]" sensecap-lorawan \
  --backend tts \
  --server https://eu1.cloud.thethings.network:8884 \
  --identity-server https://eu1.cloud.thethings.network:8884 \
  --application YOUR_APPLICATION_ID
```

Set `--identity-server` to your deployment's Identity Server if it differs from
the Application Server. Repeat `--application` for multiple applications.

Add `--list` to print the current devices and exit, or `--json` for newline-delimited
JSON output. Use `--api-key-file /path/to/key` instead of an environment variable
if preferred. Stop watching with Ctrl+C. Run `sensecap-lorawan --help` for all options.

With a pip installation, use `sensecap-lorawan` directly in place of the
`uvx --from ... sensecap-lorawan` prefix. `python -m sensecap_lorawan` also works.

## Python

```python
from lorawan_connection.backend.chirpstack import ChirpStackConnection
from sensecap_lorawan import SenseCapDeviceCollection


async def list_sensors(
    endpoint: str, api_key: str, tenant: str, application: str
) -> None:
    connection = ChirpStackConnection(
        endpoint,
        api_key,
        tenant_id=tenant,
        application_ids=[application],
        network_id=endpoint,
    )
    devices = SenseCapDeviceCollection(connection)
    try:
        await connection.async_connect()
        await devices.async_setup()
        for device in devices.devices.values():
            print(device.descriptor.name, type(device).__name__)
    finally:
        devices.close()
        await connection.close()
```

The collection also accepts a `TTSConnection`. Subscribe with
`devices.subscribe_device_added(listener)` and `device.add_update_listener(listener)`
to receive live readings. Values remain `None` until the sensor reports them.

### Reading measurements

Existing properties such as `S2101.temperature`, `S2101.humidity`, and
`S2102.illuminance` remain available. All models also expose
`measurements[channel][measurement_id]`, whose `Measurement` contains `value`,
`timestamp`, and protocol-specific `attributes`. Timestamps are timezone-aware
UTC values when transmitted by the device; otherwise they are `None`.

```python
from sensecap_lorawan import S2107

payload = S2107.decode(bytes.fromhex("470000ff9c8000"))
for measurement in payload.measurements:
    print(measurement.channel, measurement.value)
# 1 0.0
# 2 -1.0
# 3 None
```

For a live device, use `device.measurement_value(4203, channel=2)` or
`device.temperature(channel=2)` on an S2107. The S2100 uses input channel numbers as measurement
IDs within channel 1, matching Seeed's decoder. Unknown seven-byte measurement
IDs are retained. See Seeed's [measurement ID list](https://wiki.seeedstudio.com/sensecraft-data-platform/api/appendix/list_of_measurement_ids/)
for their meanings and units.

`metadata` contains reported versions, intervals, model information, and errors.
`battery_percentage` reads the battery value from the vendor payload;
`battery_level` remains the standardized LoRaWAN status value. Tracker event
measurements contain numeric event IDs, positioning status is a numeric code,
and Wi-Fi/BLE scan values are lists of `{mac, rssi}` dictionaries.

Direct decoding raises `ValueError` for malformed or unknown frame layouts. Live
models discard those payloads atomically. Partial updates retain other readings;
older readings cannot replace newer values on the same channel and measurement ID.
Device timestamps take precedence over receipt time for buffered readings.
Fault/absent values become `None`; zero remains a valid reading. The seven-byte
protocol's two-byte trailer is not CRC-validated, matching Seeed's decoder.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run mypy
uv build
```

Tests include captured S2101/S2102 uplinks, reference outputs for every decoder
family, and malformed, partial, and out-of-order messages.
See [fixture provenance and regeneration](tests/fixtures/README.md).

## Releases

The source version stays `0.0.0`. Publishing a GitHub release named `0.1.0`, for
example, builds that version and publishes it to PyPI through Trusted Publishing.
See [RELEASING.md](RELEASING.md) for the one-time publisher setup.

## License

Apache-2.0. Extracted from the SenseCAP examples in
[`lorawan-connection`](https://github.com/home-assistant-libs/lorawan-connection).
