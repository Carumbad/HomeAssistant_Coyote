"""Bluetooth connection and streaming coordinator for Coyote devices."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BATTERY_UUID_V2,
    BATTERY_UUID_V3,
    CONF_PROTOCOL,
    DOMAIN,
    NOTIFY_UUID_V3,
    PATTERN_A_UUID_V2,
    PATTERN_B_UUID_V2,
    POWER_UUID_V2,
    STREAM_INTERVAL,
    WRITE_UUID_V3,
    Pattern,
    ProtocolVersion,
)
from .protocol import (
    CoyoteState,
    encode_v2_pattern,
    encode_v2_power,
    encode_v3_b0,
    parse_v2_power,
    parse_v3_notification,
)

_LOGGER = logging.getLogger(__name__)


class CoyoteCoordinator(DataUpdateCoordinator[CoyoteState]):
    """Own a Coyote connection and its time-sensitive waveform stream."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.address = entry.unique_id or entry.data["address"]
        self.protocol = ProtocolVersion(entry.data[CONF_PROTOCOL])
        self.state = CoyoteState(protocol=self.protocol)
        self._client: BleakClientWithServiceCache | None = None
        self._connect_lock = asyncio.Lock()
        self._stream_task: asyncio.Task[None] | None = None
        self._tick = 0
        self._sequence = 0
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.address}",
            update_interval=timedelta(minutes=5),
        )

    def _ble_device(self) -> BLEDevice:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise UpdateFailed(
                "Device is not available through a connectable Bluetooth "
                "adapter or proxy"
            )
        return device

    async def _ensure_connected(self) -> BleakClientWithServiceCache:
        async with self._connect_lock:
            if self._client is not None and self._client.is_connected:
                return self._client
            device = self._ble_device()
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self.entry.title,
                disconnected_callback=self._on_disconnect,
            )
            if self.protocol is ProtocolVersion.V3:
                await self._client.start_notify(NOTIFY_UUID_V3, self._notification_v3)
            else:
                await self._client.start_notify(POWER_UUID_V2, self._notification_v2)
            self.state.connected = True
            self.async_set_updated_data(self.state)
            return self._client

    @callback
    def _on_disconnect(self, _client: Any) -> None:
        self._client = None
        self.state.connected = False
        # Never resume stimulation implicitly after an adapter/proxy interruption.
        # A fresh explicit switch-on is required.
        self.state.enabled = False
        self.async_set_updated_data(self.state)

    @callback
    def _notification_v3(self, _characteristic: Any, data: bytearray) -> None:
        parsed = parse_v3_notification(bytes(data))
        if parsed is not None:
            _sequence, self.state.actual_a, self.state.actual_b = parsed
            self.async_set_updated_data(self.state)

    @callback
    def _notification_v2(self, _characteristic: Any, data: bytearray) -> None:
        try:
            self.state.actual_a, self.state.actual_b = parse_v2_power(bytes(data))
        except ValueError:
            _LOGGER.debug("Ignoring malformed V2 power notification: %s", data.hex())
            return
        self.async_set_updated_data(self.state)

    async def _async_update_data(self) -> CoyoteState:
        temporary = not self.state.enabled
        try:
            client = await self._ensure_connected()
            uuid = (
                BATTERY_UUID_V3
                if self.protocol is ProtocolVersion.V3
                else BATTERY_UUID_V2
            )
            value = await client.read_gatt_char(uuid)
            self.state.battery = value[0] if value else None
        except Exception as err:
            raise UpdateFailed(f"Unable to read Coyote: {err}") from err
        finally:
            if temporary:
                await self._disconnect()
        return self.state

    async def async_set_enabled(self, enabled: bool) -> None:
        """Start or safely stop waveform output."""
        if enabled == self.state.enabled:
            return
        self.state.enabled = enabled
        if enabled:
            self._stream_task = self.hass.async_create_task(
                self._stream_loop(), f"Coyote stream {self.address}"
            )
        else:
            task, self._stream_task = self._stream_task, None
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await self._write_stop()
            await self._disconnect()
        self.async_set_updated_data(self.state)

    async def _stream_loop(self) -> None:
        """Maintain the protocol's 100 ms waveform cadence."""
        try:
            client = await self._ensure_connected()
            first = True
            while self.state.enabled:
                if self.protocol is ProtocolVersion.V3:
                    sequence = self._next_sequence() if first else 0
                    packet = encode_v3_b0(
                        self.state, sequence=sequence, absolute_intensity=first
                    )
                    await client.write_gatt_char(WRITE_UUID_V3, packet, response=True)
                else:
                    if first:
                        await client.write_gatt_char(
                            POWER_UUID_V2,
                            encode_v2_power(
                                self.state.channel_a.intensity,
                                self.state.channel_b.intensity,
                            ),
                            response=True,
                        )
                    await client.write_gatt_char(
                        PATTERN_A_UUID_V2,
                        encode_v2_pattern(self.state.channel_a, self._tick),
                        response=True,
                    )
                    await client.write_gatt_char(
                        PATTERN_B_UUID_V2,
                        encode_v2_pattern(self.state.channel_b, self._tick),
                        response=True,
                    )
                first = False
                self._tick = (self._tick + 1) % 4
                await asyncio.sleep(STREAM_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.warning("Coyote stream interrupted: %s", err)
            self.state.connected = False
            self.state.enabled = False
            self.async_set_updated_data(self.state)
            await self._disconnect()

    def _next_sequence(self) -> int:
        self._sequence = self._sequence % 15 + 1
        return self._sequence

    async def async_apply_state(self) -> None:
        """Push changed intensity immediately when output is active."""
        if not self.state.enabled:
            self.async_set_updated_data(self.state)
            return
        client = await self._ensure_connected()
        if self.protocol is ProtocolVersion.V3:
            await client.write_gatt_char(
                WRITE_UUID_V3,
                encode_v3_b0(
                    self.state,
                    sequence=self._next_sequence(),
                    absolute_intensity=True,
                ),
                response=True,
            )
        else:
            await client.write_gatt_char(
                POWER_UUID_V2,
                encode_v2_power(
                    self.state.channel_a.intensity, self.state.channel_b.intensity
                ),
                response=True,
            )
        self.async_set_updated_data(self.state)

    async def _write_stop(self) -> None:
        try:
            client = await self._ensure_connected()
            if self.protocol is ProtocolVersion.V3:
                await client.write_gatt_char(
                    WRITE_UUID_V3,
                    encode_v3_b0(
                        self.state,
                        sequence=self._next_sequence(),
                        absolute_intensity=True,
                        force_zero=True,
                    ),
                    response=True,
                )
            else:
                await client.write_gatt_char(
                    POWER_UUID_V2, encode_v2_power(0, 0), response=True
                )
            self.state.actual_a = 0
            self.state.actual_b = 0
        except Exception as err:
            _LOGGER.warning("Could not send final stop command: %s", err)

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        if client is not None and client.is_connected:
            await client.disconnect()
        self.state.connected = False

    async def async_shutdown(self) -> None:
        """Stop output and release Bluetooth resources."""
        if self.state.enabled:
            await self.async_set_enabled(False)
        else:
            await self._disconnect()

    async def async_set_channel_value(self, channel: str, key: str, value: Any) -> None:
        """Update one desired channel value."""
        target = self.state.channel_a if channel == "a" else self.state.channel_b
        if key == "pattern":
            target.pattern = Pattern(value)
        else:
            setattr(target, key, int(value))
        await self.async_apply_state()
