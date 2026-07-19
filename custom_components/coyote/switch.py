"""Switch entities for Coyote."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CoyoteCoordinator
from .entity import CoyoteEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the output switch."""
    async_add_entities([CoyoteOutputSwitch(entry.runtime_data)])


class CoyoteOutputSwitch(CoyoteEntity, SwitchEntity):
    """Enable the time-sensitive waveform stream."""

    _attr_translation_key = "output"
    _attr_icon = "mdi:pulse"

    def __init__(self, coordinator: CoyoteCoordinator) -> None:
        super().__init__(coordinator, "output")

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.enabled

    async def async_turn_on(self, **kwargs: object) -> None:
        await self.coordinator.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        await self.coordinator.async_set_enabled(False)
