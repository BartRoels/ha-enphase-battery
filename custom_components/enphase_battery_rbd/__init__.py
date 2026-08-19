"""Enphase Battery RBD — Home Assistant integration.

Controls the Enphase IQ Battery Restrict Battery Discharge (RBD) feature
via the Enlighten cloud batterySettings API, using a fully authenticated
browser-like session (cookie jar + XSRF token).

This is the only approach confirmed to work for homeowner accounts:
  PUT /service/batteryConfig/api/v1/batterySettings/{battery_id}
      ?userId={user_id}&source=enho
  { "rbdControl": { "enabled": true|false } }

The batterySettings endpoint requires:
  - e-auth-token: JWT from /app-api/jwt_token.json
  - x-xsrf-token: BP-XSRF-Token cookie from /schedules/isValid
  - Full Enlighten session cookies (especially the session cookie)
  - origin / referer: battery-profile-ui.enphaseenergy.com
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import EnlightenSession
from .const import CONF_BATTERY_ID, CONF_EMAIL, CONF_PASSWORD, CONF_USER_ID, DOMAIN
from .coordinator import EnphaseBatteryCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SWITCH, Platform.SENSOR]

type EnphaseBatteryConfigEntry = ConfigEntry[EnphaseBatteryCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: EnphaseBatteryConfigEntry
) -> bool:
    """Set up Enphase Battery RBD from a config entry."""
    session = EnlightenSession(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        battery_id=entry.data.get(CONF_BATTERY_ID),
        user_id=entry.data.get(CONF_USER_ID),
    )

    coordinator = EnphaseBatteryCoordinator(hass, session)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnphaseBatteryConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.session.close()
    return unload_ok
