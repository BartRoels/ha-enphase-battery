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


async def _validate_credentials(email: str, password: str) -> tuple[str, str]:
    """Validate Enlighten credentials and return (battery_id, user_id)."""
    session = EnlightenSession(email=email, password=password)
    try:
        await session.login()
        return session.battery_id, session.user_id
    finally:
        await session.close()


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
                battery_id, user_id = await _validate_credentials(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except EnlightenAuthError as err:
                _LOGGER.warning("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during setup: %s", err)
                errors["base"] = "cannot_connect"
            else:
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

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials expire or change."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-auth confirmation — user re-enters their password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                battery_id, user_id = await _validate_credentials(
                    user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except EnlightenAuthError as err:
                _LOGGER.warning("Re-auth failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during re-auth: %s", err)
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    reauth_entry,
                    data={
                        **reauth_entry.data,
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_BATTERY_ID: battery_id,
                        CONF_USER_ID: user_id,
                    },
                )
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=reauth_entry.data.get(CONF_EMAIL, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
