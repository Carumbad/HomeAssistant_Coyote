"""Pure protocol encoders and decoders for DG-LAB Coyote V2 and V3."""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import Pattern, ProtocolVersion


@dataclass
class ChannelState:
    """Desired output state for one channel."""

    intensity: int = 0
    frequency: int = 80
    waveform_strength: int = 20
    pattern: Pattern = Pattern.STEADY


@dataclass
class CoyoteState:
    """Desired and reported device state."""

    protocol: ProtocolVersion
    enabled: bool = False
    battery: int | None = None
    connected: bool = False
    channel_a: ChannelState = field(default_factory=ChannelState)
    channel_b: ChannelState = field(default_factory=ChannelState)
    actual_a: int = 0
    actual_b: int = 0


V3_STRENGTH_PATTERNS: dict[Pattern, tuple[float, float, float, float]] = {
    Pattern.STEADY: (1, 1, 1, 1),
    Pattern.PULSE: (1, 0, 1, 0),
    Pattern.WAVE: (0.25, 0.5, 0.75, 1),
    Pattern.BREATHE: (0.15, 0.4, 0.7, 1),
}


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp an integer to a protocol range."""
    return max(minimum, min(maximum, int(value)))


def v3_samples(channel: ChannelState) -> tuple[list[int], list[int]]:
    """Build four frequency/strength samples for a V3 channel."""
    frequency = clamp(channel.frequency, 10, 240)
    strength = clamp(channel.waveform_strength, 0, 100)
    multipliers = V3_STRENGTH_PATTERNS[channel.pattern]
    return [frequency] * 4, [round(strength * item) for item in multipliers]


def encode_v3_b0(
    state: CoyoteState,
    *,
    sequence: int = 0,
    absolute_intensity: bool = False,
    force_zero: bool = False,
) -> bytes:
    """Encode the 20-byte V3 B0 intensity and waveform command."""
    mode = 0x0F if absolute_intensity else 0
    intensity_a = 0 if force_zero else clamp(state.channel_a.intensity, 0, 200)
    intensity_b = 0 if force_zero else clamp(state.channel_b.intensity, 0, 200)
    frequencies_a, strengths_a = v3_samples(state.channel_a)
    frequencies_b, strengths_b = v3_samples(state.channel_b)
    return bytes(
        [0xB0, ((sequence & 0x0F) << 4) | mode, intensity_a, intensity_b]
        + frequencies_a
        + strengths_a
        + frequencies_b
        + strengths_b
    )


def encode_v3_bf(
    limit_a: int,
    limit_b: int,
    frequency_balance_a: int = 0,
    frequency_balance_b: int = 0,
    strength_balance_a: int = 0,
    strength_balance_b: int = 0,
) -> bytes:
    """Encode V3 persistent soft limits and balance parameters."""
    return bytes(
        [
            0xBF,
            clamp(limit_a, 0, 200),
            clamp(limit_b, 0, 200),
            clamp(frequency_balance_a, 0, 255),
            clamp(frequency_balance_b, 0, 255),
            clamp(strength_balance_a, 0, 255),
            clamp(strength_balance_b, 0, 255),
        ]
    )


def parse_v3_notification(data: bytes) -> tuple[int, int, int] | None:
    """Parse a V3 B1 sequence and actual channel strengths."""
    if len(data) < 4 or data[0] != 0xB1:
        return None
    return data[1] & 0x0F, data[2], data[3]


def encode_v2_power(power_a: int, power_b: int) -> bytes:
    """Encode V2 packed 11-bit A/B power values, on-air byte order."""
    a = clamp(power_a, 0, 2047)
    b = clamp(power_b, 0, 2047)
    logical = bytes([(a >> 5) & 0x3F, ((a & 0x1F) << 3) | (b >> 8), b & 0xFF])
    return logical[::-1]


def parse_v2_power(data: bytes) -> tuple[int, int]:
    """Parse V2 packed A/B power values."""
    if len(data) != 3:
        raise ValueError("V2 power value must be exactly 3 bytes")
    logical = data[::-1]
    a = (logical[0] << 5) | (logical[1] >> 3)
    b = ((logical[1] & 0x07) << 8) | logical[2]
    return a, b


def _v2_xyz(channel: ChannelState, tick: int) -> tuple[int, int, int]:
    """Convert common controls into one V2 X/Y/Z waveform sample."""
    frequency_hz = clamp(channel.frequency, 1, 100)
    x = clamp(round((1000 / frequency_hz / 1000) ** 0.5 * 15), 1, 31)
    y = clamp(round(1000 / frequency_hz) - x, 0, 1023)
    z = clamp(round(channel.waveform_strength * 31 / 100), 0, 31)
    factors = V3_STRENGTH_PATTERNS[channel.pattern]
    return x, y, round(z * factors[tick % 4])


def encode_v2_pattern(channel: ChannelState, tick: int = 0) -> bytes:
    """Encode a packed V2 X/Y/Z waveform command."""
    x, y, z = _v2_xyz(channel, tick)
    logical = bytes([(z >> 1) & 0x0F, ((z & 1) << 7) | (y >> 3), ((y & 7) << 5) | x])
    return logical[::-1]
