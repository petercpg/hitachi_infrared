"""Config flow for Hitachi Infrared Remote integration."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_COOL_ONLY,
    CONF_EMITTER_ENTITY_ID,
    CONF_ENABLE_DISPLAY_CONTROL,
    CONF_ENABLE_FROST_WASH,
    CONF_ENABLE_MOLD_PREVENTION,
    CONF_ENABLE_PM25,
    CONF_ENABLE_SOMATOSENSORY,
    CONF_ENABLE_TIMER,
    CONF_ENCODING,
    CONF_H_SWING_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_PROTOCOL,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_NAME,
    DOMAIN,
    SWING_MODE_MULTI_STEP,
    SWING_MODE_SIMPLE,
)


class HitachiIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hitachi Infrared."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return HitachiIROptionsFlowHandler()

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
            user_input.setdefault(CONF_PROTOCOL, "ac344")
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
                vol.Required(CONF_ENCODING, default="broadlink"): SelectSelector(
                    SelectSelectorConfig(
                        options=["broadlink", "pronto", "raw"],
                        translation_key="encoding",
                    )
                ),
                vol.Optional(CONF_TEMPERATURE_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_HUMIDITY_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_COOL_ONLY, default=False): bool,
                vol.Required(
                    CONF_H_SWING_MODE, default=SWING_MODE_SIMPLE
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[SWING_MODE_SIMPLE, SWING_MODE_MULTI_STEP],
                        translation_key="h_swing_mode",
                    )
                ),
                vol.Required(CONF_ENABLE_DISPLAY_CONTROL, default=False): bool,
                vol.Required(CONF_ENABLE_SOMATOSENSORY, default=False): bool,
                vol.Required(CONF_ENABLE_MOLD_PREVENTION, default=False): bool,
                vol.Required(CONF_ENABLE_FROST_WASH, default=False): bool,
                vol.Required(CONF_ENABLE_PM25, default=False): bool,
                vol.Required(CONF_ENABLE_TIMER, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class HitachiIROptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Hitachi IR Remote integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            title = user_input.get("name") or DEFAULT_NAME
            # Update config entry data and title
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=title,
                data={**self.config_entry.data, **user_input},
            )
            return self.async_create_entry(title="", data={})

        current = self.config_entry.data
        options_schema = vol.Schema(
            {
                vol.Optional(
                    "name",
                    description={"suggested_value": current.get("name")},
                ): str,
                vol.Required(
                    CONF_EMITTER_ENTITY_ID,
                    description={
                        "suggested_value": current.get(CONF_EMITTER_ENTITY_ID)
                    },
                ): EntitySelector(EntitySelectorConfig(domain=["infrared", "remote"])),
                vol.Required(
                    CONF_ENCODING,
                    default=current.get(CONF_ENCODING, "broadlink"),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=["broadlink", "pronto", "raw"],
                        translation_key="encoding",
                    )
                ),
                vol.Optional(
                    CONF_TEMPERATURE_SENSOR,
                    description={
                        "suggested_value": current.get(CONF_TEMPERATURE_SENSOR)
                    },
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Optional(
                    CONF_HUMIDITY_SENSOR,
                    description={"suggested_value": current.get(CONF_HUMIDITY_SENSOR)},
                ): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(
                    CONF_COOL_ONLY,
                    default=current.get(CONF_COOL_ONLY, False),
                ): bool,
                vol.Required(
                    CONF_H_SWING_MODE,
                    default=current.get(CONF_H_SWING_MODE, SWING_MODE_SIMPLE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[SWING_MODE_SIMPLE, SWING_MODE_MULTI_STEP],
                        translation_key="h_swing_mode",
                    )
                ),
                vol.Required(
                    CONF_ENABLE_DISPLAY_CONTROL,
                    default=current.get(CONF_ENABLE_DISPLAY_CONTROL, False),
                ): bool,
                vol.Required(
                    CONF_ENABLE_SOMATOSENSORY,
                    default=current.get(CONF_ENABLE_SOMATOSENSORY, False),
                ): bool,
                vol.Required(
                    CONF_ENABLE_MOLD_PREVENTION,
                    default=current.get(CONF_ENABLE_MOLD_PREVENTION, False),
                ): bool,
                vol.Required(
                    CONF_ENABLE_FROST_WASH,
                    default=current.get(CONF_ENABLE_FROST_WASH, False),
                ): bool,
                vol.Required(
                    CONF_ENABLE_PM25,
                    default=current.get(CONF_ENABLE_PM25, False),
                ): bool,
                vol.Required(
                    CONF_ENABLE_TIMER,
                    default=current.get(CONF_ENABLE_TIMER, True),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
