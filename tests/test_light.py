"""Decode light readings and retain the latest valid value."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from lorawan_connection import DeviceDescriptor, UplinkEvent

from sensecap_lorawan import S2102


@pytest.mark.parametrize("stack", ["chirpstack", "tts"])
def test_light_updates(stack: str) -> None:
    """Both catalog identities decode readings and reject invalid or stale data."""
    brand_id, model_id = S2102.identifiers[stack]
    descriptor = DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name="Light",
        application_id="application",
        profile_id="profile",
        stack=stack,
        brand_id=brand_id,
        model_id=model_id,
    )
    device = S2102(descriptor)
    event = UplinkEvent(
        descriptor=descriptor,
        received_at=datetime(2026, 10, 8, tzinfo=UTC),
        f_port=2,
        data=bytes.fromhex("010310a08601000000"),
    )
    device._receive_event(event)
    assert device.illuminance == 100
    device._receive_event(replace(event, data=b"\x01"))
    device._receive_event(replace(event, data=bytes.fromhex("010310ffffffff0000")))
    device._receive_event(replace(event, f_port=99))
    device._receive_event(replace(event, data=bytes.fromhex("020310000000000000")))
    device._receive_event(
        replace(
            event,
            received_at=event.received_at - timedelta(seconds=1),
            data=bytes.fromhex("010310000000000000"),
        )
    )
    assert device.illuminance == 100
    device._receive_event(replace(event, data=bytes.fromhex("010310ffffff7f0000")))
    assert device.illuminance is None
    device.close()
    device._receive_event(event)
    assert device.illuminance is None
