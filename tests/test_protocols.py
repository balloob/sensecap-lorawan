"""Protocol boundaries and live device behavior beyond the reference decoders."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from lorawan_connection import AddedEvent, DeviceDescriptor, UplinkEvent
from lorawan_connection.mock import MockConnection

from sensecap_lorawan import (
    A1102,
    S2100,
    S2101,
    S2103,
    S2104,
    S2105,
    S2106,
    S2107,
    S2120,
    T1000,
    T1000E,
    T2000,
    WM1110,
    SenseCapDeviceCollection,
)
from sensecap_lorawan.blocks import decode_blocks
from sensecap_lorawan.records import decode_records
from sensecap_lorawan.trackers import decode_tracker

NOW = datetime(2026, 10, 14, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"


def descriptor(model):
    return DeviceDescriptor(
        network_id="network",
        dev_eui="0201010101010101",
        name=model.__name__,
        application_id="app",
        profile_id="profile",
        stack="chirpstack",
        brand_id=0x02E8,
        model_id="explicit-model",
    )


def uplink(device, data, **kwargs):
    return UplinkEvent(
        descriptor=device.descriptor,
        received_at=NOW,
        data=data,
        f_port=device._ports[0],
        **kwargs,
    )


def records(*values):
    return b"".join(
        bytes([channel])
        + mid.to_bytes(2, "little")
        + value.to_bytes(4, "little", signed=True)
        for channel, mid, value in values
    ) + bytes(2)


@pytest.mark.parametrize(
    ("model", "data", "expected"),
    [
        (
            S2103,
            records((1, 4097, 21500), (1, 4098, 60000), (1, 4100, 450000)),
            {"temperature": 21.5, "humidity": 60, "co2": 450},
        ),
        (
            S2104,
            records((1, 4102, -4500), (1, 4103, 25800)),
            {"soil_temperature": -4.5, "soil_moisture": 25.8},
        ),
        (
            S2105,
            records((1, 4102, 20000), (1, 4103, 50000), (1, 4108, 2500)),
            {"soil_temperature": 20, "soil_moisture": 50, "conductivity": 2.5},
        ),
        (
            S2106,
            records((1, 4097, 24000), (1, 4106, 7200)),
            {"temperature": 24, "ph": 7.2},
        ),
        (
            S2120,
            bytes.fromhex("0100d732000186a019002302010e0000303927934c00570001869f"),
            {
                "temperature": 21.5,
                "humidity": 50,
                "illuminance": 100000,
                "uv_index": 2.5,
                "wind_speed": 3.5,
                "wind_direction": 270,
                "rainfall": 12.345,
                "pressure": 101310,
                "wind_gust": 8.7,
                "rain_accumulation": 99.999,
            },
        ),
    ],
)
def test_model_readings(model, data, expected):
    device = model(descriptor(model))
    listener = Mock()
    device.add_update_listener(listener)
    event = uplink(device, data)
    device._receive_event(event)
    assert {name: getattr(device, name) for name in expected} == expected
    listener.assert_called_once_with()
    device._receive_event(replace(event, data=data[:-1]))
    device._receive_event(replace(event, f_port=99))
    assert listener.call_count == 1
    device.close()
    device._receive_event(event)
    assert listener.call_count == 1


def test_catalog_discovery():
    """Every advertised identity exists in a separately captured official catalog."""
    catalog = json.loads((FIXTURES / "catalog.json").read_text())
    chirpstack_ids = {value["id"] for value in catalog["chirpstack"].values()}
    for stack in ("chirpstack", "tts"):
        collection = SenseCapDeviceCollection(MockConnection(stack_type=stack))
        identities = set()
        for index, model in enumerate(SenseCapDeviceCollection.DEVICES):
            if stack not in model.identifiers:
                continue
            brand, model_id = model.identifiers[stack]
            assert (brand, model_id) not in identities
            identities.add((brand, model_id))
            assert model_id in (
                chirpstack_ids if stack == "chirpstack" else catalog["tts"]
            )
            desc = replace(
                descriptor(model),
                stack=stack,
                brand_id=brand,
                model_id=model_id,
                dev_eui=f"{index:016x}",
            )
            collection.handle_event(AddedEvent(descriptor=desc, received_at=NOW))
            assert type(collection.devices[desc.dev_eui]) is model
        collection.close()


def test_models_without_catalog_identity():
    for model in (A1102, T1000E, WM1110):
        assert not model.identifiers
        assert model not in SenseCapDeviceCollection.DEVICES


def test_record_metadata_and_unknown_measurements():
    data = bytes.fromhex("0000000101000100070064003c00") + records((2, 6000, -250))
    result = decode_records(data)
    assert result.metadata == {
        "hardware_version": "1.0",
        "firmware_version": "1.1",
        "battery_percentage": 100,
        "measurement_interval": 3600,
    }
    assert result.measurements[0].channel == 2
    assert result.measurements[0].id == 6000
    assert result.measurements[0].value == -0.25
    device = S2101(descriptor(S2101))
    device._receive_event(uplink(device, data))
    assert device.battery_percentage == 100
    assert device.battery_level is None


def test_sensor_metadata_by_channel():
    data = bytes.fromhex(
        "02020001020304020300050607080209000001020302200100000000"
    ) + bytes(2)
    result = decode_records(data)
    assert result.metadata == {
        "sensor_2_id": "0807060504030201",
        "detection_type": 3,
        "model_id": 2,
        "model_version": 1,
        "sensor_2_removed": True,
    }


def test_s2107_zero_absent_and_historical_readings():
    device = S2107(descriptor(S2107))
    event = uplink(device, bytes.fromhex("470000ff9c8000"))
    device._receive_event(event)
    assert [device.temperature(i) for i in (1, 2, 3)] == [0, -1, None]
    older = (
        bytes([0x46])
        + int((NOW - timedelta(hours=1)).timestamp()).to_bytes(4, "big")
        + bytes.fromhex("07d007d007d0")
    )
    device._receive_event(
        replace(event, data=older, received_at=NOW + timedelta(seconds=1))
    )
    assert [device.temperature(i) for i in (1, 2, 3)] == [0, -1, None]
    # A newer buffered reading uses its collection time, not delivery time.
    newer = (
        bytes([0x46])
        + int((NOW + timedelta(hours=1)).timestamp()).to_bytes(4, "big")
        + bytes.fromhex("07d007d007d0")
    )
    device._receive_event(
        replace(event, data=newer, received_at=NOW + timedelta(hours=2))
    )
    assert [device.temperature(i) for i in (1, 2, 3)] == [20, 20, 20]
    assert device.measurements[1][4203].timestamp == NOW + timedelta(hours=1)


def test_datalogger_channels():
    result = S2100.decode(bytes.fromhex("30120000003039ffffd8f032340000000000007530"))
    assert {m.id: m.value for m in result.measurements} == {
        1: 12.345,
        2: -10,
        3: 0,
        4: 30,
    }


@pytest.mark.parametrize(("model_id", "expected"), [(60113, 12.34), (60242, 12.35)])
def test_vision_model_in_later_frame(model_id, expected):
    payload = bytes.fromhex("30120000003034fffffc18")
    payload += bytes.fromhex("331a00fffffc18") + (
        (1_000_000 + model_id) * 1000
    ).to_bytes(4, "big")
    result = A1102.decode(payload)
    assert result.metadata["model_id"] == model_id
    assert result.measurements[0].value == pytest.approx(expected)
    assert result.measurements[1].id == 4174


def test_tracker_location_and_port():
    device = T1000(descriptor(T1000))
    data = bytes.fromhex("0600004001") + int(NOW.timestamp()).to_bytes(4, "big")
    data += (-122_500_000).to_bytes(4, "big", signed=True) + (37_250_000).to_bytes(
        4, "big", signed=True
    )
    data += bytes.fromhex("ff83000064")
    event = uplink(device, data)
    device._receive_event(event)
    assert (
        device.longitude,
        device.latitude,
        device.temperature,
        device.light,
        device.battery_percentage,
    ) == (-122.5, 37.25, -12.5, 0, 100)
    assert device.measurement_value(4200) == [7]
    assert device.measurements[1][4197].attributes["motion_id"] == 1
    device._receive_event(replace(event, data=data[:-1] + bytes([50]), f_port=192))
    assert device.battery_percentage == 100


def test_wm1110_null_custom_measurements():
    result = WM1110.decode(bytes.fromhex("171100000165000000800000000000002a"))
    assert {m.id: m.value for m in result.measurements} == {
        4208: 1,
        4165: None,
        4166: 42,
    }


def test_tracker_scans_and_fragments():
    data = bytes.fromhex("2301640000000002aabbccddeeffc4ffffffffffff80")
    result = T1000E.decode(data)
    assert result.measurements[-1].value == [{"mac": "aa:bb:cc:dd:ee:ff", "rssi": -60}]
    fragment = decode_tracker(bytes.fromhex("0e21000703aabbcc"))
    assert fragment.measurements[0].value == "aabbcc"
    assert fragment.measurements[0].attributes == {
        "count": 2,
        "index": 1,
        "group_id": 7,
    }
    assert T2000.decode(b"\x0c").metadata == {"time_sync_requested": True}


@pytest.mark.parametrize("family", ["t1000", "t1000e", "t2000", "wm1110"])
def test_unknown_tracker_frames(family):
    with pytest.raises(ValueError):
        decode_tracker(b"\xff", family)


def test_all_truncated_single_frames():
    cases = json.loads((FIXTURES / "reference.json").read_text())
    for case in cases:
        family = case["family"]
        if family in ("S210X", "A1101", "Gen1"):
            continue
        data = bytes.fromhex(case["payload"])
        for end in range(len(data)):
            with pytest.raises(ValueError):
                if family in ("S2100", "S2107", "S2120", "A1102"):
                    decode_blocks(data[:end], vision=family == "A1102")
                else:
                    decode_tracker(data[:end], family.lower())


def test_invalid_suffix_is_atomic():
    device = S2107(descriptor(S2107))
    device._receive_event(uplink(device, bytes.fromhex("4707d007d007d0ff")))
    assert device.measurements == {}
    assert device.metadata == {}


@pytest.mark.parametrize("model", [S2100, S2107, S2120, A1102])
def test_block_models_use_port_three(model):
    device = model(descriptor(model))
    event = UplinkEvent(
        descriptor=device.descriptor,
        received_at=NOW,
        f_port=3,
        data=bytes.fromhex("39640100020000050000"),
    )
    device._receive_event(event)
    assert device.battery_percentage == 100
    device._receive_event(
        replace(event, f_port=99, data=bytes.fromhex("39320100020000050000"))
    )
    assert device.battery_percentage == 100


def test_weather_unsigned_fields():
    """The vendor manual defines UV, light, wind, rain and pressure as unsigned."""
    result = S2120.decode(
        bytes.fromhex("4aff9c6480000000c8ffff4bffff80000000ffff4cffff80000000")
    )
    values = {item.id: item.value for item in result.measurements}
    assert values == {
        4097: -10,
        4098: 100,
        4099: 2147483648,
        4190: 20,
        4105: 6553.5,
        4104: 65535,
        4113: 2147483.648,
        4101: 655350,
        4191: 6553.5,
        4213: 2147483.648,
    }


def test_metadata_keeps_newest_report():
    device = S2101(descriptor(S2101))
    event = uplink(device, bytes.fromhex("000700640005000000"))
    device._receive_event(event)
    device._receive_event(
        replace(
            event,
            received_at=NOW - timedelta(seconds=1),
            data=bytes.fromhex("000700320005000000"),
        )
    )
    assert device.battery_percentage == 100


def test_wm1110_absent_event_status():
    result = WM1110.decode(bytes.fromhex("170d800000650000000000002a"))
    assert result.measurements[0].value is None


def test_t2000_rejects_oversized_uuid_filter():
    data = bytearray([0x27]) + bytearray(45)
    data[29] = 17
    with pytest.raises(ValueError, match="UUID filter"):
        T2000.decode(data)
