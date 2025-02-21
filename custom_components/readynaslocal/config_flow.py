"""Config flow for ReadyNAS integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SSL
from .pyreadynas import ReadyNASAPI
from .const import DOMAIN  # Add DOMAIN import


class ReadyNASConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ReadyNAS integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_USERNAME): str,
                        vol.Required(CONF_PASSWORD): str,
                        vol.Optional(CONF_SSL, default=True): bool,
                        vol.Optional("ignore_ssl_errors", default=True): bool,
                    }
                ),
            )

        try:
            # Initialize API with user input
            api = ReadyNASAPI(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                use_ssl=user_input.get(CONF_SSL, True),  # Changed default to True
                ignore_ssl_errors=user_input.get("ignore_ssl_errors", True),
            )

            # Test connection
            if not await api.get_health_info():
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_HOST): str,
                            vol.Required(CONF_USERNAME): str,
                            vol.Required(CONF_PASSWORD): str,
                            vol.Optional(
                                CONF_SSL, default=True
                            ): bool,  # Changed default to True
                            vol.Optional("ignore_ssl_errors", default=True): bool,
                        }
                    ),
                    errors={"base": "cannot_connect"},
                )

            # Create unique ID based on host
            await self.async_set_unique_id(f"readynas_{user_input[CONF_HOST]}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"ReadyNAS ({user_input[CONF_HOST]})", data=user_input
            )

        except Exception as ex:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_USERNAME): str,
                        vol.Required(CONF_PASSWORD): str,
                        vol.Optional(
                            CONF_SSL, default=True
                        ): bool,  # Changed default to True
                        vol.Optional("ignore_ssl_errors", default=True): bool,
                    }
                ),
                errors={"base": "unknown"},
            )
