"""Config flow for DG-LAB Coyote Bluetooth devices."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from .const import (
    CONF_PROTOCOL,
    DOMAIN,
    SERVICE_UUID_V2,
    SERVICE_UUID_V3,
    ProtocolVersion,
)


def _detect_protocol(
    name: str | None, service_uuids: list[str]
) -> ProtocolVersion | None:
    lowered = {item.lower() for item in service_uuids}
    if SERVICE_UUID_V3 in lowered or (name and name.startswith("47L121")):
        return ProtocolVersion.V3
    if SERVICE_UUID_V2 in lowered or (name and name.startswith("D-LAB")):
        return ProtocolVersion.V2
    return None


class CoyoteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Discover and configure a Coyote."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: bluetooth.BluetoothServiceInfoBleak | None = None
        self._protocol: ProtocolVersion | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        protocol = _detect_protocol(discovery_info.name, discovery_info.service_uuids)
        if protocol is None or not discovery_info.connectable:
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self._protocol = protocol
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        if self._discovery is None or self._protocol is None:
            return self.async_abort(reason="not_supported")
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery.name,
                data={
                    CONF_ADDRESS: self._discovery.address,
                    CONF_PROTOCOL: self._protocol.value,
                },
            )
        self._set_confirm_only()
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select from connectable discovered devices."""
        discoveries: dict[
            str, tuple[bluetooth.BluetoothServiceInfoBleak, ProtocolVersion]
        ] = {}
        for info in bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        ):
            protocol = _detect_protocol(info.name, info.service_uuids)
            if protocol is not None:
                discoveries[info.address] = (info, protocol)

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            if address not in discoveries:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In({})}),
                    errors={"base": "cannot_connect"},
                )
            info, protocol = discoveries[address]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=info.name,
                data={CONF_ADDRESS: address, CONF_PROTOCOL: protocol.value},
            )

        if not discoveries:
            return self.async_abort(reason="no_devices_found")
        choices = {
            address: f"{info.name} ({protocol.value.upper()}, {address})"
            for address, (info, protocol) in discoveries.items()
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(choices)}),
        )
