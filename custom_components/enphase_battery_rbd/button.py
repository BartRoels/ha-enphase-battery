"""Button platform for Enphase Battery RBD."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTON_RECREATE_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import EnphaseBatteryCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enphase Battery RBD buttons."""
    coordinator: EnphaseBatteryCoordinator = entry.runtime_data
    async_add_entities([RecreateRBDScheduleButton(coordinator, entry)])


class RecreateRBDScheduleButton(ButtonEntity):
    """Button to recreate the default 24h RBD schedule.

    Useful if the schedule was accidentally deleted from the Enphase app.
    Creates a fresh 00:00–23:59 all-days schedule — the same one
    the integration creates automatically during initial setup.
    """

    _attr_has_entity_name = True
    _attr_name = BUTTON_RECREATE_NAME
    _attr_icon = "mdi:calendar-sync"

    def __init__(
        self,
        coordinator: EnphaseBatteryCoordinator,
        entry: ConfigEntry,
    ) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_recreate_schedule"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.session.battery_id or entry.entry_id)},
            name=f"Enphase Battery (site {coordinator.session.battery_id})",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_press(self) -> None:
        """Recreate the default RBD schedule."""
        _LOGGER.info(
            "Recreating default RBD schedule for site %s",
            self._coordinator.session.battery_id,
        )
        await self._coordinator.session.create_default_schedule(
            timezone=self.hass.config.time_zone
        )
        await self._coordinator.async_request_refresh()
