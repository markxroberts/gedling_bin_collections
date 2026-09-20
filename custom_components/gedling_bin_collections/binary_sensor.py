"""Binary sensor platform for Gedling Bin Collections."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import SERVICE_NAMES
from .coordinator import GedlingBinCoordinator
from .entity import GedlingBinEntity
from .models import BinCollection


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the collection-tomorrow binary sensor."""
    coordinator: GedlingBinCoordinator = entry.runtime_data
    async_add_entities(
        [GedlingCollectionTomorrowBinarySensor(coordinator, entry.entry_id)]
    )


class GedlingCollectionTomorrowBinarySensor(GedlingBinEntity, BinarySensorEntity):
    """Indicate whether one or more bin collections are due tomorrow."""

    _attr_name = "Collection tomorrow"
    _attr_translation_key = "collection_tomorrow"

    @property
    def icon(self) -> str:
        """Return an icon reflecting whether collection is due tomorrow."""
        return "mdi:delete-alert" if self.is_on else "mdi:delete-outline"

    def __init__(self, coordinator: GedlingBinCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_collection_tomorrow"

    async def async_added_to_hass(self) -> None:
        """Register a midnight refresh in addition to coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._handle_midnight,
                hour=0,
                minute=0,
                second=0,
            )
        )

    @callback
    def _handle_midnight(self, now: datetime) -> None:
        """Re-evaluate the relative date when the local day changes."""
        self.async_write_ha_state()

    def _tomorrow_collection(self) -> BinCollection | None:
        tomorrow = dt_util.now().date() + timedelta(days=1)
        for collection in self.coordinator.data.collections:
            if collection.date == tomorrow:
                return collection
            if collection.date > tomorrow:
                break
        return None

    @property
    def is_on(self) -> bool:
        """Return true when a collection is due tomorrow."""
        return self._tomorrow_collection() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of tomorrow's collection."""
        collection = self._tomorrow_collection()
        attrs: dict[str, Any] = {
            "address": self.coordinator.data.address,
            "source_url": self.coordinator.data.source_url,
        }
        if collection is None:
            return attrs

        attrs["collection_date"] = collection.date.isoformat()
        attrs["collections"] = [
            SERVICE_NAMES.get(service, service.replace("_", " ").title())
            for service in collection.services
        ]
        attrs["raw_collections"] = list(collection.raw_services)
        return attrs
