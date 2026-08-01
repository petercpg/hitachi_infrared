"""The Hitachi Infrared Remote integration."""

import contextlib
import importlib.metadata
import json
import logging
import pathlib
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_integration

from .const import DOMAIN as DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]


def _get_manifest_version() -> str:
    """Read integration version dynamically from manifest.json."""
    try:
        manifest_path = pathlib.Path(__file__).parent / "manifest.json"
        data = json.loads(manifest_path.read_text())
        return data.get("version", "unknown")
    except Exception:
        return "unknown"


def _log_version_info(integration_version: str) -> None:
    """Log integration version and base infrared-protocols package version at DEBUG level."""
    base_version = "unknown"
    with contextlib.suppress(importlib.metadata.PackageNotFoundError):
        base_version = importlib.metadata.version("infrared-protocols")

    _LOGGER.debug(
        "Loaded Hitachi Infrared integration v%s (base infrared-protocols v%s)",
        integration_version,
        base_version,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hitachi Infrared from a config entry."""
    try:
        integration = await async_get_integration(hass, DOMAIN)
        version = integration.version or _get_manifest_version()
    except Exception:
        version = _get_manifest_version()

    _log_version_info(version)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
