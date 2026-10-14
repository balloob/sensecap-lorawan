"""Run the installed command against a simulated backend."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from lorawan_connection import DeviceDescriptor
from lorawan_connection.mock import MockConnection

from sensecap_lorawan import S2101
from sensecap_lorawan.__main__ import main


@pytest.mark.parametrize("backend", ["chirpstack", "tts"])
def test_list_devices(backend: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Both backend selections list supported devices and close the connection."""
    brand_id, model_id = S2101.identifiers[backend]
    descriptor = DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Greenhouse",
        stack=backend,
        brand_id=brand_id,
        model_id=model_id,
        application_id="application",
        profile_id="profile",
    )
    connection = MockConnection([descriptor], stack_type=backend)
    connection.inventory = AsyncMock(return_value=[descriptor])
    connection.close = AsyncMock()
    with (
        patch(
            "sys.argv",
            [
                "sensecap-lorawan",
                "--backend",
                backend,
                "--server",
                "https://example.com",
                "--list",
                "--json",
            ],
        ),
        patch(
            "lorawan_connection.cli_helper.connect_from_args", return_value=connection
        ) as connect,
    ):
        main()
    assert connect.call_args.args[0].backend == backend
    data = json.loads(capsys.readouterr().out)
    assert data["model"] == "S2101"
    assert data["name"] == "Greenhouse"
    assert data["state"]["temperature"] is None
    connection.close.assert_awaited_once_with()
