import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Regenerate fixtures from the pinned Seeed checkout."
)
parser.add_argument("source", type=Path)
root = parser.parse_args().source
cases = []


def add(family, payload, name):
    source = (
        next((root / family / "TTN").glob("*.js"))
        if family not in ("T1000E", "T1000", "Gen1")
        else {
            "T1000": root / "T1000/TTN/SenseCAP_T1000_TTN_Decoder.js",
            "T1000E": root / "T1000/TTN/SenseCAP_T1000E_TTN_Decoder.js",
            "Gen1": root
            / "SenseCAP Gen1 Sensor/SenseCAP_WirelessSensor_TTN_Decoder.js",
        }[family]
    )
    cases.append(
        dict(family=family, payload=payload.hex(), name=name, source=str(source))
    )


for family in ("S210X", "A1101", "Gen1"):
    for mid, value in (
        (4097, -10250),
        (4098, 62600),
        (4099, 100000),
        (4100, 450000),
        (4101, 101300000),
        (4102, 23500),
        (4103, 50200),
        (4106, 7200),
        (4108, 2800),
        (4175, 1010),
        (4180, 2050),
    ):
        add(
            family,
            bytes([1])
            + mid.to_bytes(2, "little")
            + value.to_bytes(4, "little", signed=True)
            + bytes(2),
            str(mid),
        )
    add(
        family,
        bytes.fromhex("0000000101000100070064003c00012001000000002890"),
        "metadata",
    )
lengths = {
    **dict.fromkeys(
        (1, 0x20, 0x21, 0x30, 0x31, 0x33, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45), 10
    ),
    2: 8,
    3: 1,
    6: 1,
    5: 4,
    0x34: 4,
    **dict.fromkeys((4, 0x10, 0x32, 0x35, 0x36, 0x37, 0x38, 0x39), 9),
}
for family in ("S2100", "S2120", "S2107", "A1102"):
    extended = lengths.copy()
    if family == "S2120":
        extended.update({0x4A: 10, 0x4B: 8, 0x4C: 6})
    if family == "S2107":
        extended.update({0x46: 10, 0x47: 6, 0x48: 10, 0x49: 7, 0x7F: 1})
    for mid, length in extended.items():
        raw = bytearray([1] * length)
        if mid in (0x30, 0x31, 0x32, 0x33, 0x35, 0x36, 0x37, 0x38):
            raw[0] = 0x12
        add(family, bytes([mid]) + raw, f"{mid:02x}")
fixed = {
    "T1000": {
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
        13: 4,
        15: 16,
        16: 12,
        17: 13,
        26: 27,
        27: 47,
        28: 40,
        29: 19,
    },
    "T1000E": {0x1E: 12, 0x1F: 20, 0x22: 14, 0x25: 12, 0x26: 6},
    "T2000": {
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
    "WM1110": {0x13: 11, 0x14: 36, 0x15: 29, 0x16: 8, 0x18: 27},
}
for family, frames in fixed.items():
    for mid, length in frames.items():
        raw = bytearray([1] * length)
        add(family, bytes([mid]) + raw, f"{mid:02x}")
for family, frames in {
    "T1000E": {0x20: 13, 0x21: 13, 0x23: 7, 0x24: 7},
    "T2000": {0x2C: 15, 0x2D: 15, 0x2F: 9, 0x30: 9},
}.items():
    for mid, pos in frames.items():
        raw = bytearray([1] * (pos + 14))
        raw[0] = mid
        raw[pos] = 2
        # Length includes header and two complete scan records.
        raw.append(1)
        add(family, raw, f"{mid:02x}-two-scans")
for family, mid in [("T1000", 0x0E), ("WM1110", 0x12)]:
    add(family, bytes([mid, 0x21, 0, 7, 3, 1, 2, 3]), "gnss-fragment")
add("WM1110", bytes.fromhex("170d000001650000000000002a"), "custom")
# Negative coordinates and a complete negative temperature uplink.
add(
    "T1000",
    bytes.fromhex("060000400165000000")
    + (-122_500_000).to_bytes(4, "big", signed=True)
    + (37_250_000).to_bytes(4, "big", signed=True)
    + (-125).to_bytes(2, "big", signed=True)
    + bytes.fromhex("000064"),
    "negative-location",
)
proc = subprocess.run(
    ["node", str(Path(__file__).with_name("reference.cjs"))],
    input="\n".join(json.dumps(c) for c in cases),
    text=True,
    capture_output=True,
    check=True,
)
out = [json.loads(line) for line in proc.stdout.splitlines()]
(Path(__file__).resolve().parents[1] / "tests/fixtures/reference.json").write_text(
    json.dumps(out, indent=2) + "\n"
)
print(
    "Generated", len(out), "cases;", sum("error" in c for c in out), "reference errors"
)
for c in out:
    if "error" in c:
        print(c["family"], c["name"], c["error"])
