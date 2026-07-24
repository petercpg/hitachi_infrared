"""The Hitachi Infrared Remote integration."""

import contextlib
import importlib.metadata
import json
import logging
from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .const import DOMAIN as DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.CLIMATE]


def _log_infrared_protocols_info() -> None:
    """Log infrared-protocols package source and version info at DEBUG level."""
    try:
        import infrared_protocols

        file_path = getattr(infrared_protocols, "__file__", "unknown")
    except ImportError as err:
        _LOGGER.debug("infrared-protocols import failed: %s", err)
        return

    version_str = "unknown"
    git_url = None
    commit_id = None
    requested_revision = None

    with contextlib.suppress(importlib.metadata.PackageNotFoundError):
        version_str = importlib.metadata.version("infrared-protocols")

    with contextlib.suppress(Exception):
        dist = importlib.metadata.distribution("infrared-protocols")
        direct_url_json = dist.read_text("direct_url.json")
        if direct_url_json:
            data = json.loads(direct_url_json)
            git_url = data.get("url")
            vcs_info = data.get("vcs_info", {})
            commit_id = vcs_info.get("commit_id")
            requested_revision = vcs_info.get("requested_revision")

    info_parts = [f"version={version_str}", f"path={file_path}"]
    if git_url:
        info_parts.append(f"git_url={git_url}")
    if requested_revision:
        info_parts.append(f"ref={requested_revision}")
    if commit_id:
        info_parts.append(f"commit={commit_id}")

    _LOGGER.debug("Loaded infrared-protocols: %s", ", ".join(info_parts))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hitachi Infrared from a config entry."""
    _log_infrared_protocols_info()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
