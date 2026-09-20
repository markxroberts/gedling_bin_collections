"""Sensor platform for Gedling Bin Collections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    SERVICE_GARDEN,
    SERVICE_GENERAL,
    SERVICE_GLASS,
    SERVICE_ICONS,
    SERVICE_NAMES,
    SERVICE_RECYCLING,
)
from .coordinator import GedlingBinCoordinator
from .entity import GedlingBinEntity
from .models import BinCollection


@dataclass(frozen=True, slots=True)
class SensorDescription:
    key: str
    name: str
    service: str | None
    icon: str
    translation_key: str


DESCRIPTIONS = (
    SensorDescription("next", "Next collection", None, "mdi:delete-clock", "next_collection"),
    SensorDescription(
        SERVICE_GENERAL,
        "Next general waste collection",
        SERVICE_GENERAL,
        SERVICE_ICONS[SERVICE_GENERAL],
        "general_collection",
    ),
    SensorDescription(
        SERVICE_RECYCLING,
        "Next recycling collection",
        SERVICE_RECYCLING,
        SERVICE_ICONS[SERVICE_RECYCLING],
        "recycling_collection",
    ),
    SensorDescription(
        SERVICE_GLASS,
        "Next glass collection",
        SERVICE_GLASS,
        SERVICE_ICONS[SERVICE_GLASS],
        "glass_collection",
    ),
    SensorDescription(
        SERVICE_GARDEN,
        "Next garden waste collection",
        SERVICE_GARDEN,
        SERVICE_ICONS[SERVICE_GARDEN],
        "garden_collection",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up date sensors and add service sensors when data becomes available."""
    coordinator: GedlingBinCoordinator = entry.runtime_data
    added_keys: set[str] = set()

    @callback
    def _add_new_sensors() -> None:
        detected = {
            service
            for collection in coordinator.data.collections
            for service in collection.services
        }
        descriptions = [
            desc
            for desc in DESCRIPTIONS
            if desc.key not in added_keys
            and (desc.service is None or desc.service in detected)
        ]
        if not descriptions:
            return

        added_keys.update(desc.key for desc in descriptions)
        async_add_entities(
            GedlingBinDateSensor(coordinator, entry.entry_id, desc)
            for desc in descriptions
        )

    # The generic Next collection sensor is available immediately.  If startup
    # occurs during a Gedling outage, type-specific sensors are added as soon as
    # the first successful retry reveals which services this property has.
    _add_new_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_sensors))


class GedlingBinDateSensor(GedlingBinEntity, SensorEntity):
    """Date sensor for the next collection of a requested type."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: GedlingBinCoordinator,
        entry_id: str,
        description: SensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self.description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key

    def _next_collection(self) -> BinCollection | None:
        today = dt_util.now().date()
        for collection in self.coordinator.data.collections:
            if collection.date < today:
                continue
            if self.description.service is None:
                return collection
            if self.description.service in collection.services:
                return collection
        return None

    @property
    def native_value(self) -> date | None:
        collection = self._next_collection()
        return collection.date if collection else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        collection = self._next_collection()
        attrs: dict[str, Any] = {
            "address": self.coordinator.data.address,
            "source_url": self.coordinator.data.source_url,
        }
        if collection is None:
            return attrs

        today = dt_util.now().date()
        attrs["days_until"] = (collection.date - today).days
        attrs["collections"] = [
            SERVICE_NAMES.get(service, service.replace("_", " ").title())
            for service in collection.services
        ]
        attrs["raw_collections"] = list(collection.raw_services)
        return attrs
