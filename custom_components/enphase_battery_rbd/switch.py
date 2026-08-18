"""Switch platform for Enphase Battery RBD."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, SWITCH_RBD_NAME
from .coordinator import EnphaseBatteryCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enphase Battery RBD switch."""
    coordinator: EnphaseBatteryCoordinator = entry.runtime_data
    async_add_entities([EnphaseBatteryRBDSwitch(coordinator, entry)])


class EnphaseBatteryRBDSwitch(CoordinatorEntity[EnphaseBatteryCoordinator], SwitchEntity):
    """Switch to enable/disable Enphase battery Restrict Battery Discharge.

    ON  = RBD enabled  = battery will NOT discharge (protected)
    OFF = RBD disabled = battery discharges normally per system profile
    """

    _attr_has_entity_name = True
    _attr_name = SWITCH_RBD_NAME
    _attr_icon = "mdi:battery-lock"

    def __init__(
        self,
        coordinator: EnphaseBatteryCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rbd"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.session.battery_id or entry.entry_id)},
            name=f"Enphase Battery (site {coordinator.session.battery_id})",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when RBD is enabled (battery discharge is restricted)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("rbd_enabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable RBD — restrict battery discharge."""
        await self.coordinator.session.set_rbd_enabled(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable RBD — allow battery to discharge normally."""
        await self.coordinator.session.set_rbd_enabled(False)
        await self.coordinator.async_request_refresh()
