# DG-LAB Coyote for Home Assistant

A HACS-compatible Bluetooth integration for local control of DG-LAB Coyote V2
and V3 pulse controllers.

![Coyote icon](custom_components/coyote/brand/icon.png)

> [!CAUTION]
> This integration controls an electrical stimulation device. Start at zero,
> set conservative limits in the official app/device, test without electrodes,
> and keep a physical means of stopping output available. Home Assistant,
> Bluetooth and automations are not safety-rated systems.

## Features

- Automatic Bluetooth discovery of Coyote V2 (`D-LAB...`) and V3 (`47L121...`)
- Home Assistant Bluetooth proxy support when the proxy supports active GATT connections
- Explicit master output switch, off by default
- Independent A/B intensity, frequency, waveform strength and waveform preset controls
- Battery percentage and device-reported A/B intensity sensors
- V2 100 ms X/Y/Z waveform streaming
- V3 20-byte B0 streaming and B1 state notifications
- Best-effort zero-output command on stop and integration unload

## Bluetooth proxies and BTHome

The integration uses Home Assistant's managed Bluetooth APIs. A compatible
ESPHome Bluetooth proxy can therefore carry the connection when it advertises
the device as **connectable** and has a free active-connection slot.

BTHome itself is a BLE advertisement data format. It does not provide the
connected GATT writes or the strict 100 ms stream required by Coyote, so a
passive/BTHome-only proxy cannot control this device.

Proxy latency and reliability matter. First test with a local Bluetooth adapter.
If using a proxy, use a recent ESPHome release, strong Wi-Fi, good BLE signal and
no heavily loaded connection slots. Loss of the waveform stream stops waveform
blocks, but it must not be treated as a certified emergency-stop mechanism.

## Installation with HACS

1. In HACS, open **Integrations**.
2. Add this GitHub repository as a custom repository of type **Integration**.
3. Download **DG-LAB Coyote** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Search for **DG-LAB Coyote** and select the discovered device.

The device must not already be connected to the official app. Bluetooth LE
peripherals generally accept only one controller connection at a time.

## Safe first run

1. Leave electrodes disconnected.
2. Confirm both desired intensity controls are zero.
3. Select a waveform and enable **Output**.
4. Raise one channel slowly.
5. Turn **Output** off and confirm both reported intensities return to zero.
6. Only proceed after testing disconnect and proxy-loss behaviour for your setup.

Changing controls while Output is off only updates the desired state. Enabling
Output applies the selected intensities and begins the 100 ms stream.

## Supported protocols

| Model | Advertising name | GATT protocol |
|---|---|---|
| Coyote V2 | `D-LAB ESTIM01` / `D-LAB...` | Separate power and A/B pattern characteristics |
| Coyote V3 | `47L121000` / `47L121...` | Combined B0 command and B1 notification |

Protocol references:

- [Official DG-LAB Bluetooth protocol](https://github.com/dungeonlab-open/dglab-bluetooth-protocol)
- [Historical V2 Web Bluetooth example](https://rezreal.github.io/coyote/web-bluetooth-example.html)

The upstream protocol repository includes its own usage restrictions. Review
those terms before commercial use. This project is independent and is not
endorsed by DG-LAB.

## Current limitations

- V3 persistent BF soft-limit and balance settings are intentionally not changed.
- The included presets are simple generated waveforms, not copies of official app patterns.
- Hardware testing is required across firmware revisions.
- Bluetooth disconnect cannot guarantee delivery of the final zero command.

## Development

Pure protocol tests can be run with:

```bash
python -m unittest discover -s tests
```

Home Assistant validation should be run with Hassfest and the HACS validation action.
