"""DataUpdateCoordinator for Enphase Battery RBD."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EnlightenApiError, EnlightenAuthError, EnlightenSession
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class EnphaseBatteryCoordinator(DataUpdateCoordinator[dict]):
    """Coordinator that keeps the Enlighten session alive and fetches RBD state."""

    def __init__(self, hass: HomeAssistant, session: EnlightenSession) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.session = session
        self._rbd_enabled: bool | None = None

    async def _async_update_data(self) -> dict:
        """Refresh the Enlighten session and fetch current RBD state."""
        try:
            await self.session.ensure_authenticated()
            rbd_status = await self.session.get_rbd_status()
            self._rbd_enabled = rbd_status
            return {
                "rbd_enabled": rbd_status,
                "session_ok": True,
                "battery_id": self.session.battery_id,
                "user_id": self.session.user_id,
            }
        except EnlightenAuthError as err:
            # Trigger the re-auth flow so HA notifies the user
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed(
                f"Enlighten authentication failed — re-enter your credentials: {err}"
            ) from err
        except EnlightenApiError as err:
            raise UpdateFailed(f"Enlighten API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    @property
    def rbd_enabled(self) -> bool | None:
        """Return the last known RBD enabled state."""
        return self._rbd_enabled
