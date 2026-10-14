# Captured uplinks

These S2101 and S2102 application payloads were captured from physical devices on
8 October 2026. Payload bytes and FPorts are unchanged. Device identifiers,
server addresses, custom profile UUIDs, and credentials are omitted.

Expected values were checked against the
[SenseCAP reference decoder](https://github.com/TheThingsNetwork/lorawan-devices/blob/7693223153369c9d6ded148c335b454cd318c756/vendor/sensecap/sensecap210x-common-decoder.js).
Tests use synthetic descriptors with the official model identities.


## Reference decoder outputs

`reference.json` contains synthetic wire frames and their outputs from Seeed's
JavaScript decoders at commit
[`d0a234205fb9574dd03abd49561b60c243c0d1e3`](https://github.com/Seeed-Solution/SenseCAP-Decoder/tree/d0a234205fb9574dd03abd49561b60c243c0d1e3).
These are generated protocol examples, not physical-device captures. The original
JavaScript is not bundled or used at runtime. Tests normalize numeric strings,
event IDs, positioning status codes, and MAC address casing before comparison.

With Node.js installed, regenerate them from that source revision:

```sh
python scripts/generate_reference.py /path/to/SenseCAP-Decoder
```

Independent tests cover behavior where the reference decoder is permissive or
loses information: truncated frames are rejected atomically, zero probe readings
are retained, absent values are explicit `None`, and WM1110 custom channels keep
their positions when another channel is absent. Tracker frame timestamps use UTC;
frames without a device timestamp use receipt time when updating a live model.
The T1000-E reference uses the current wall clock for these frames; we do not
present decoder execution time as a device-provided timestamp.

`catalog.json` records the official catalog entries used for discovery checks.
Its commit fields pin ChirpStack's device profiles and The Things Network's
LoRaWAN Device Repository. No private profile UUIDs are included.


Weather quantities other than temperature are decoded as unsigned, as specified
in the [S2120 user guide](https://files.seeedstudio.com/products/SenseCAP/101990961_SenseCAP%20S2120/SenseCAP%20S2120%20LoRaWAN%208-in-1%20Weather%20Station%20User%20Guide.pdf),
section 10.2. This corrects the JavaScript helper's signed interpretation when the
high bit is set, including UV index values above 12.7.
