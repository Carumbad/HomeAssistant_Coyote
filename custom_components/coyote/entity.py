"""Base entity for the Coyote integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CoyoteCoordinator


class CoyoteEntity(CoordinatorEntity[CoyoteCoordinator]):
    """Base class for Coyote entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CoyoteCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            manufacturer=MANUFACTURER,
            model=f"Coyote {coordinator.protocol.value.upper()}",
            name=coordinator.entry.title,
        )
