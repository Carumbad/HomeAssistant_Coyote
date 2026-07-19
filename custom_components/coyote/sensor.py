"""Sensors for Coyote."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CoyoteCoordinator
from .entity import CoyoteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Coyote sensors."""
    coordinator: CoyoteCoordinator = entry.runtime_data
    async_add_entities(
        [
            CoyoteBatterySensor(coordinator),
            CoyoteActualIntensitySensor(coordinator, "a"),
            CoyoteActualIntensitySensor(coordinator, "b"),
        ]
    )


class CoyoteBatterySensor(CoyoteEntity, SensorEntity):
    """Battery percentage."""

    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CoyoteCoordinator) -> None:
        super().__init__(coordinator, "battery")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.state.battery


class CoyoteActualIntensitySensor(CoyoteEntity, SensorEntity):
    """Device-reported channel intensity."""

    _attr_translation_key = "actual_intensity"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:lightning-bolt-circle"

    def __init__(self, coordinator: CoyoteCoordinator, channel: str) -> None:
        super().__init__(coordinator, f"channel_{channel}_actual_intensity")
        self._channel = channel
        self._attr_translation_placeholders = {"channel": channel.upper()}

    @property
    def native_value(self) -> int:
        return (
            self.coordinator.state.actual_a
            if self._channel == "a"
            else self.coordinator.state.actual_b
        )
