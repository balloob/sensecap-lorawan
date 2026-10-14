"""Compare wire values with pinned Seeed JavaScript decoder output."""

import json
from pathlib import Path

import pytest

from sensecap_lorawan.blocks import decode_blocks
from sensecap_lorawan.records import decode_records
from sensecap_lorawan.trackers import decode_tracker

CASES = json.loads((Path(__file__).parent / "fixtures/reference.json").read_text())


def flatten(value):
    if isinstance(value, list):
        for item in value:
            yield from flatten(item)
    elif isinstance(value, dict):
        yield value


def normalized(mid, value):
    if mid in (4200, 5003):
        return [item["id"] for item in value]
    if mid == 3576 and isinstance(value, dict):
        return value["id"]
    if mid in (5001, 5002):
        return [{"mac": item["mac"].lower(), "rssi": item["rssi"]} for item in value]
    if mid in (6152, 3979):
        return value.lower()
    if (
        isinstance(value, str)
        and mid not in (3001, 3502, 4174)
        and not 4175 <= mid <= 4184
    ):
        return float(value)
    return value


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['family']}-{c['name']}")
def test_reference_measurements(case):
    family = case["family"]
    data = bytes.fromhex(case["payload"])
    if family in ("S210X", "A1101", "Gen1"):
        result = decode_records(data)
    elif family in ("S2100", "S2107", "S2120", "A1102"):
        result = decode_blocks(data, vision=family == "A1102")
    else:
        result = decode_tracker(data, family.lower())
    values = {(item.channel, item.id): item for item in result.measurements}
    for expected in flatten(case["expected"]["data"]["messages"]):
        if "measurementId" not in expected or not (
            "measurementValue" in expected or "value" in expected
        ):
            continue
        mid = int(expected["measurementId"])
        channel = int(expected.get("measurementChannel", 1))
        value = normalized(mid, expected.get("measurementValue", expected.get("value")))
        actual = values[channel, mid]
        if isinstance(value, (float, int)):
            assert actual.value == pytest.approx(value)
        else:
            assert actual.value == value
        if "timestamp" in expected and actual.timestamp is not None:
            assert actual.timestamp.timestamp() * 1000 == expected["timestamp"]
        for name in ("index", "count"):
            if name in expected:
                assert actual.attributes[name] == expected[name]
        if "groupId" in expected:
            assert actual.attributes["group_id"] == expected["groupId"]
