"""Tests for Coyote protocol encoding."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType
import unittest

# Load the pure modules without importing the Home Assistant-dependent package
# __init__.py. This keeps protocol tests runnable in a plain Python checkout.
ROOT = Path(__file__).parents[1] / "custom_components" / "coyote"
package = ModuleType("custom_components.coyote")
package.__path__ = [str(ROOT)]  # type: ignore[attr-defined]
sys.modules["custom_components.coyote"] = package
for module_name in ("const", "protocol"):
    spec = spec_from_file_location(
        f"custom_components.coyote.{module_name}", ROOT / f"{module_name}.py"
    )
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from custom_components.coyote.const import Pattern, ProtocolVersion  # noqa: E402
from custom_components.coyote.protocol import (  # noqa: E402
    CoyoteState,
    encode_v2_pattern,
    encode_v2_power,
    encode_v3_b0,
    parse_v2_power,
    parse_v3_notification,
)


class ProtocolTests(unittest.TestCase):
    """Protocol test cases."""

    def test_v3_python_reference_packet(self) -> None:
        state = CoyoteState(protocol=ProtocolVersion.V3)
        state.channel_a.intensity = 0x14
        state.channel_b.intensity = 0x14
        state.channel_a.frequency = state.channel_b.frequency = 0x50
        state.channel_a.waveform_strength = state.channel_b.waveform_strength = 0x20
        self.assertEqual(
            encode_v3_b0(state, absolute_intensity=True),
            bytes.fromhex("b00f141450505050202020205050505020202020"),
        )

    def test_v3_stop_and_notification(self) -> None:
        state = CoyoteState(protocol=ProtocolVersion.V3)
        state.channel_a.intensity = 100
        state.channel_b.intensity = 80
        packet = encode_v3_b0(
            state, sequence=3, absolute_intensity=True, force_zero=True
        )
        self.assertEqual(packet[:4], bytes.fromhex("b03f0000"))
        self.assertEqual(len(packet), 20)
        self.assertEqual(
            parse_v3_notification(bytes.fromhex("b1030a14")), (3, 10, 20)
        )

    def test_v2_power_round_trip_and_known_zero(self) -> None:
        self.assertEqual(encode_v2_power(0, 0), b"\x00\x00\x00")
        for a, b in ((7, 14), (1024, 2047), (2047, 0)):
            self.assertEqual(parse_v2_power(encode_v2_power(a, b)), (a, b))

    def test_v2_pattern_is_three_bytes(self) -> None:
        state = CoyoteState(protocol=ProtocolVersion.V2)
        state.channel_a.pattern = Pattern.WAVE
        self.assertEqual(len(encode_v2_pattern(state.channel_a, 2)), 3)


if __name__ == "__main__":
    unittest.main()
