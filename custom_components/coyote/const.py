"""Constants for the Coyote integration."""

from __future__ import annotations

from enum import StrEnum

DOMAIN = "coyote"
NAME = "DG-LAB Coyote"
MANUFACTURER = "DG-LAB"

CONF_PROTOCOL = "protocol"

BATTERY_UUID_V3 = "00001500-0000-1000-8000-00805f9b34fb"
SERVICE_UUID_V3 = "0000180c-0000-1000-8000-00805f9b34fb"
WRITE_UUID_V3 = "0000150a-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID_V3 = "0000150b-0000-1000-8000-00805f9b34fb"

UUID_BASE_V2 = "955a{:04x}-0fe2-f5aa-a094-84b8d4f3e8ad"
SERVICE_UUID_V2 = UUID_BASE_V2.format(0x180B)
BATTERY_SERVICE_UUID_V2 = UUID_BASE_V2.format(0x180A)
BATTERY_UUID_V2 = UUID_BASE_V2.format(0x1500)
POWER_UUID_V2 = UUID_BASE_V2.format(0x1504)
# Despite the historical characteristic labels, the official/web examples map
# channel A to 0x1506 and channel B to 0x1505.
PATTERN_A_UUID_V2 = UUID_BASE_V2.format(0x1506)
PATTERN_B_UUID_V2 = UUID_BASE_V2.format(0x1505)

STREAM_INTERVAL = 0.1


class ProtocolVersion(StrEnum):
    """Supported protocol versions."""

    V2 = "v2"
    V3 = "v3"


class Pattern(StrEnum):
    """Built-in waveform patterns."""

    STEADY = "steady"
    PULSE = "pulse"
    WAVE = "wave"
    BREATHE = "breathe"
