"""Base entity for Gedling Bin Collections."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OFFICIAL_SEARCH_URL
from .coordinator import GedlingBinCoordinator


class GedlingBinEntity(CoordinatorEntity[GedlingBinCoordinator]):
    """Base class for entities backed by the Gedling coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GedlingBinCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Gedling bin collections",
            manufacturer="Gedling Borough Council",
            model="Waste collection service",
            configuration_url=data.source_url if data else OFFICIAL_SEARCH_URL,
        )
