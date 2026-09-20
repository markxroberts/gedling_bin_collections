"""Gedling Bin Collections integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import GedlingBinClient
from .const import CONF_CALENDAR_URL
from .coordinator import GedlingBinCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gedling Bin Collections from a config entry.

    The council website is not required to be reachable for the config entry
    itself to load.  This is intentional: an ordinary coordinator refresh can
    honour UpdateFailed.retry_after, whereas async_config_entry_first_refresh()
    keeps the entry in SETUP_RETRY and ignores retry_after until a fetch succeeds.
    """
    session = async_get_clientsession(hass)
    client = GedlingBinClient(session, entry.data[CONF_CALENDAR_URL])
    coordinator = GedlingBinCoordinator(hass, entry, client)

    # Make runtime data available before platforms are forwarded.  The
    # coordinator contains a safe empty data object until the first successful
    # council fetch, allowing the entities to be created even during an outage.
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Run the first fetch in the background.  eager_start=False is important:
    # async_setup_entry can return and Home Assistant can mark the config entry
    # LOADED before any slow/unreachable council request starts.
    entry.async_create_background_task(
        hass,
        coordinator.async_refresh(),
        "Gedling bin collections initial refresh",
        eager_start=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the saved calendar URL changes."""
    await hass.config_entries.async_reload(entry.entry_id)
