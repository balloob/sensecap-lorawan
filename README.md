# SenseCAP LoRaWAN

Read SenseCAP sensors through ChirpStack or The Things Stack using
[`lorawan-connection`](https://github.com/home-assistant-libs/lorawan-connection).

| Model | Readings |
| --- | --- |
| S2101 | Air temperature (°C), relative humidity (%) |
| S2102 | Light intensity (lux) |

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

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run mypy
uv build
```

Tests include captured S2101 and S2102 uplinks, with device identifiers and server
credentials removed. See [fixture provenance](tests/fixtures/README.md).

## Releases

The source version stays `0.0.0`. Publishing a GitHub release named `0.1.0`, for
example, builds that version and publishes it to PyPI through Trusted Publishing.
See [RELEASING.md](RELEASING.md) for the one-time publisher setup.

## License

Apache-2.0. Extracted from the SenseCAP examples in
[`lorawan-connection`](https://github.com/home-assistant-libs/lorawan-connection).
