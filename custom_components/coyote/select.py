"""Waveform preset selectors for Coyote."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import Pattern
from .coordinator import CoyoteCoordinator
from .entity import CoyoteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up waveform selectors."""
    coordinator: CoyoteCoordinator = entry.runtime_data
    async_add_entities(
        [CoyotePatternSelect(coordinator, "a"), CoyotePatternSelect(coordinator, "b")]
    )


class CoyotePatternSelect(CoyoteEntity, SelectEntity):
    """Select a simple waveform pattern."""

    _attr_translation_key = "pattern"
    _attr_icon = "mdi:chart-bell-curve-cumulative"
    _attr_options = [item.value for item in Pattern]

    def __init__(self, coordinator: CoyoteCoordinator, channel: str) -> None:
        super().__init__(coordinator, f"channel_{channel}_pattern")
        self._channel = channel
        self._attr_translation_placeholders = {"channel": channel.upper()}

    @property
    def current_option(self) -> str:
        target = (
            self.coordinator.state.channel_a
            if self._channel == "a"
            else self.coordinator.state.channel_b
        )
        return target.pattern.value

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_channel_value(self._channel, "pattern", option)
