"""Switch platform for Hitachi Infrared Remote integration."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_ENABLE_MOLD_PREVENTION, DEFAULT_NAME, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hitachi IR switch entities from config entry."""
    config = {**config_entry.data, **config_entry.options}
    entities: list[SwitchEntity] = []
    unique_id = config_entry.unique_id or config_entry.entry_id
    name = config.get("name") or DEFAULT_NAME

    climate_entity = hass.data[DOMAIN][config_entry.entry_id].get("climate")

    if config.get(CONF_ENABLE_MOLD_PREVENTION, False):
        entities.append(
            HitachiMoldPreventionSwitch(
                climate_entity=climate_entity,
                unique_id=f"{unique_id}_mold_prevention_switch",
                device_name=name,
            )
        )

    if entities:
        async_add_entities(entities)


class HitachiMoldPreventionSwitch(SwitchEntity):
    """Switch entity for Hitachi Mold Prevention / Ionization feature."""

    _attr_has_entity_name = True
    _attr_translation_key = "mold_prevention_switch"
    _attr_icon = "mdi:shield-bug-outline"

    def __init__(self, climate_entity, unique_id: str, device_name: str) -> None:
        """Initialize mold prevention switch."""
        self._climate = climate_entity
        self._attr_unique_id = unique_id
        self._device_name = device_name

    @property
    def is_on(self) -> bool:
        """Return True if mold prevention feature is enabled."""
        if self._climate and hasattr(self._climate, "mold_prevention"):
            return self._climate.mold_prevention
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on mold prevention feature."""
        if self._climate:
            duration = getattr(self._climate, "mold_duration_mins", 30)
            await self._climate.async_set_mold_prevention(True, duration)
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off mold prevention feature."""
        if self._climate:
            duration = getattr(self._climate, "mold_duration_mins", 30)
            await self._climate.async_set_mold_prevention(False, duration)
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
