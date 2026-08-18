"""Config flow for Enphase Battery RBD."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import EnlightenAuthError, EnlightenSession
from .const import CONF_BATTERY_ID, CONF_EMAIL, CONF_PASSWORD, CONF_USER_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EnphaseBatteryRBDConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enphase Battery RBD."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = EnlightenSession(
                    email=user_input[CONF_EMAIL],
                    password=user_input[CONF_PASSWORD],
                )
                await session.login()
                battery_id = session.battery_id
                user_id = session.user_id
                await session.close()

            except EnlightenAuthError as err:
                _LOGGER.warning("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during setup: %s", err)
                errors["base"] = "cannot_connect"
            else:
                # Prevent duplicate entries for same site
                await self.async_set_unique_id(battery_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Enphase Battery (site {battery_id})",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_BATTERY_ID: battery_id,
                        CONF_USER_ID: user_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
