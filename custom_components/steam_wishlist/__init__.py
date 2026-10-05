"""The Steam Wishlists integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import WishlistCoordinator

PLATFORMS = [Platform.SENSOR]

type WishlistConfigEntry = ConfigEntry[WishlistCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: WishlistConfigEntry) -> bool:
    coordinator = WishlistCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WishlistConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _reload(hass: HomeAssistant, entry: WishlistConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
