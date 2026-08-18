"""Sensor platform for Enphase Battery RBD."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_SESSION_NAME
from .coordinator import EnphaseBatteryCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enphase Battery RBD sensors."""
    coordinator: EnphaseBatteryCoordinator = entry.runtime_data
    async_add_entities([EnlightenSessionStatusSensor(coordinator, entry)])


class EnlightenSessionStatusSensor(
    CoordinatorEntity[EnphaseBatteryCoordinator], SensorEntity
):
    """Sensor showing the health of the Enlighten cloud session."""

    _attr_has_entity_name = True
    _attr_name = SENSOR_SESSION_NAME
    _attr_icon = "mdi:cloud-check"

    def __init__(
        self,
        coordinator: EnphaseBatteryCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_session"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.session.battery_id or entry.entry_id)},
            name=f"Enphase Battery (site {coordinator.session.battery_id})",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self) -> str:
        """Return OK when the session is authenticated, ERROR otherwise."""
        if self.coordinator.last_update_success and self.coordinator.data:
            return "OK" if self.coordinator.data.get("session_ok") else "ERROR"
        return "ERROR"

    @property
    def extra_state_attributes(self) -> dict:
        """Return session diagnostic attributes."""
        data = self.coordinator.data or {}
        return {
            "battery_id": data.get("battery_id"),
            "user_id": data.get("user_id"),
            "authenticated": self.coordinator.session.is_authenticated,
        }
