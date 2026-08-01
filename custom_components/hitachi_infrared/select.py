"""Select platform for Hitachi Infrared Remote integration."""

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_ENABLE_DISPLAY_CONTROL,
    CONF_ENABLE_MOLD_PREVENTION,
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
    """Set up Hitachi IR select entities from config entry."""
    config = {**config_entry.data, **config_entry.options}
    entities: list[SelectEntity] = []
    unique_id = config_entry.unique_id or config_entry.entry_id
    name = config.get("name") or DEFAULT_NAME

    climate_entity = hass.data[DOMAIN][config_entry.entry_id].get("climate")

    if config.get(CONF_ENABLE_DISPLAY_CONTROL, False):
        entities.append(
            HitachiDisplaySelect(
                climate_entity=climate_entity,
                unique_id=f"{unique_id}_display_select",
                device_name=name,
            )
        )

    if config.get(CONF_ENABLE_MOLD_PREVENTION, False):
        entities.append(
            HitachiMoldDurationSelect(
                climate_entity=climate_entity,
                unique_id=f"{unique_id}_mold_duration_select",
                device_name=name,
            )
        )

    if entities:
        async_add_entities(entities)


class HitachiDisplaySelect(SelectEntity):
    """Select entity for Hitachi AC Display Brightness."""

    _attr_has_entity_name = True
    _attr_translation_key = "display_select"

    def __init__(self, climate_entity, unique_id: str, device_name: str) -> None:
        """Initialize display brightness select entity."""
        self._climate = climate_entity
        self._attr_unique_id = unique_id
        self._device_name = device_name
        self._attr_options = ["bright", "medium", "dim", "off"]

    @property
    def current_option(self) -> str | None:
        """Return currently selected display brightness."""
        if self._climate and hasattr(self._climate, "display"):
            return self._climate.display
        return "bright"

    async def async_select_option(self, option: str) -> None:
        """Change selected display brightness."""
        if self._climate:
            await self._climate.async_set_display(option)
            self.async_write_ha_state()

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


class HitachiMoldDurationSelect(SelectEntity):
    """Select entity for Mold Prevention Duration."""

    _attr_has_entity_name = True
    _attr_translation_key = "mold_duration_select"

    def __init__(self, climate_entity, unique_id: str, device_name: str) -> None:
        """Initialize mold duration select entity."""
        self._climate = climate_entity
        self._attr_unique_id = unique_id
        self._device_name = device_name
        self._attr_options = ["10", "20", "30", "45", "60"]

    @property
    def current_option(self) -> str | None:
        """Return currently selected duration in minutes."""
        if self._climate and hasattr(self._climate, "mold_duration_mins"):
            return str(self._climate.mold_duration_mins)
        return "30"

    async def async_select_option(self, option: str) -> None:
        """Change selected duration in minutes."""
        if self._climate:
            active = getattr(self._climate, "mold_prevention", False)
            await self._climate.async_set_mold_prevention(active, int(option))
            self.async_write_ha_state()

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
