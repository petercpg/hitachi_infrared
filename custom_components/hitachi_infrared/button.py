"""Button platform for Hitachi Infrared Remote integration."""

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_ENABLE_FROST_WASH,
    CONF_ENABLE_PM25,
    DEFAULT_NAME,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hitachi IR button entities from config entry."""
    config = {**config_entry.data, **config_entry.options}
    entities: list[ButtonEntity] = []
    unique_id = config_entry.unique_id or config_entry.entry_id
    name = config.get("name") or DEFAULT_NAME

    climate_entity = hass.data[DOMAIN][config_entry.entry_id].get("climate")

    if config.get(CONF_ENABLE_FROST_WASH, False):
        entities.append(
            HitachiFrostWashButton(
                climate_entity=climate_entity,
                unique_id=f"{unique_id}_frost_wash_button",
                device_name=name,
            )
        )

    if config.get(CONF_ENABLE_PM25, False):
        entities.append(
            HitachiPM25Button(
                climate_entity=climate_entity,
                unique_id=f"{unique_id}_pm25_button",
                device_name=name,
            )
        )

    if entities:
        async_add_entities(entities)


class HitachiFrostWashButton(ButtonEntity):
    """Button entity for Frost Wash / Freeze Clean feature."""

    _attr_has_entity_name = True
    _attr_translation_key = "frost_wash_button"
    _attr_icon = "mdi:snowflake-melt"

    def __init__(self, climate_entity, unique_id: str, device_name: str) -> None:
        """Initialize Frost Wash button entity."""
        self._climate = climate_entity
        self._attr_unique_id = unique_id
        self._device_name = device_name

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._climate:
            await self._climate.async_run_clean()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for linking entity."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self._climate.unique_id if self._climate else self._attr_unique_id,
                )
            },
            name=self._device_name,
            manufacturer="Hitachi",
            model="AC (IR)",
        )


class HitachiPM25Button(ButtonEntity):
    """Button entity for toggling PM2.5 display on indoor unit."""

    _attr_has_entity_name = True
    _attr_translation_key = "pm25_button"
    _attr_icon = "mdi:air-filter"

    def __init__(self, climate_entity, unique_id: str, device_name: str) -> None:
        """Initialize PM2.5 toggle button entity."""
        self._climate = climate_entity
        self._attr_unique_id = unique_id
        self._device_name = device_name

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._climate:
            await self._climate.async_set_pm25()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for linking entity."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    self._climate.unique_id if self._climate else self._attr_unique_id,
                )
            },
            name=self._device_name,
            manufacturer="Hitachi",
            model="AC (IR)",
        )
