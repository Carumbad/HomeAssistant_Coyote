"""Number controls for Coyote channels."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ProtocolVersion
from .coordinator import CoyoteCoordinator
from .entity import CoyoteEntity


@dataclass(frozen=True, kw_only=True)
class CoyoteNumberDescription(NumberEntityDescription):
    """Describe a channel number."""

    state_key: str


DESCRIPTIONS = (
    CoyoteNumberDescription(
        key="intensity",
        translation_key="intensity",
        state_key="intensity",
        icon="mdi:lightning-bolt",
    ),
    CoyoteNumberDescription(
        key="frequency",
        translation_key="frequency",
        state_key="frequency",
        icon="mdi:sine-wave",
    ),
    CoyoteNumberDescription(
        key="waveform_strength",
        translation_key="waveform_strength",
        state_key="waveform_strength",
        icon="mdi:waveform",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up channel number controls."""
    coordinator: CoyoteCoordinator = entry.runtime_data
    async_add_entities(
        CoyoteChannelNumber(coordinator, channel, description)
        for channel in ("a", "b")
        for description in DESCRIPTIONS
    )


class CoyoteChannelNumber(CoyoteEntity, NumberEntity):
    """A desired channel parameter."""

    entity_description: CoyoteNumberDescription

    def __init__(
        self,
        coordinator: CoyoteCoordinator,
        channel: str,
        description: CoyoteNumberDescription,
    ) -> None:
        super().__init__(coordinator, f"channel_{channel}_{description.key}")
        self.entity_description = description
        self._channel = channel
        self._attr_translation_placeholders = {"channel": channel.upper()}
        if description.key == "intensity":
            self._attr_native_min_value = 0
            self._attr_native_max_value = (
                200 if coordinator.protocol is ProtocolVersion.V3 else 2047
            )
            self._attr_native_step = (
                1 if coordinator.protocol is ProtocolVersion.V3 else 7
            )
        elif description.key == "frequency":
            self._attr_native_min_value = (
                10 if coordinator.protocol is ProtocolVersion.V3 else 1
            )
            self._attr_native_max_value = (
                240 if coordinator.protocol is ProtocolVersion.V3 else 100
            )
            self._attr_native_step = 1
            self._attr_native_unit_of_measurement = "Hz"
        else:
            self._attr_native_min_value = 0
            self._attr_native_max_value = 100
            self._attr_native_step = 1
            self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> float:
        target = (
            self.coordinator.state.channel_a
            if self._channel == "a"
            else self.coordinator.state.channel_b
        )
        return float(getattr(target, self.entity_description.state_key))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_channel_value(
            self._channel, self.entity_description.state_key, round(value)
        )
