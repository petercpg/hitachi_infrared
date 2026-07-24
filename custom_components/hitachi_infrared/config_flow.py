"""Config flow for Hitachi Infrared Remote integration."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    CONF_COOL_ONLY,
    CONF_EMITTER_ENTITY_ID,
    CONF_HUMIDITY_SENSOR,
    CONF_PROTOCOL,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_NAME,
    DOMAIN,
)


class HitachiIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hitachi Infrared."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent configuring the same emitter twice
            await self.async_set_unique_id(
                f"hitachi_ir_{user_input[CONF_EMITTER_ENTITY_ID]}"
            )
            self._abort_if_unique_id_configured()

            title = user_input.get("name") or DEFAULT_NAME
            return self.async_create_entry(
                title=title,
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional("name"): str,
                vol.Required(CONF_EMITTER_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(domain=["infrared", "remote"])
                ),
                vol.Optional(CONF_TEMPERATURE_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_HUMIDITY_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_PROTOCOL, default="ac344"): vol.In(
                    ["ac344", "ac280"]
                ),
                vol.Required(CONF_COOL_ONLY, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
