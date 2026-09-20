"""Calendar platform for Gedling Bin Collections."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import SERVICE_NAMES, SERVICE_ORDER
from .coordinator import GedlingBinCoordinator
from .entity import GedlingBinEntity
from .models import BinCollection


def _friendly_service(service: str) -> str:
    return SERVICE_NAMES.get(service, service.replace("_", " ").title())


def _summary(collection: BinCollection) -> str:
    names = [_friendly_service(item) for item in collection.services]
    if len(names) == 1:
        return f"{names[0]} collection"
    return " + ".join(names)


def _event(collection: BinCollection, address: str | None) -> CalendarEvent:
    return CalendarEvent(
        start=collection.date,
        end=collection.date + timedelta(days=1),
        summary=_summary(collection),
        description="Official Gedling Borough Council bin collection",
        location=address,
        uid=f"gedling-bin-{collection.date.isoformat()}-{'-'.join(collection.services)}",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: GedlingBinCoordinator = entry.runtime_data
    async_add_entities([GedlingBinCalendar(coordinator, entry.entry_id)])


class GedlingBinCalendar(GedlingBinEntity, CalendarEntity):
    """Read-only calendar containing future bin collection dates."""

    # This calendar is the main feature of the Gedling collection
    # device.  With has_entity_name=True, name=None makes Home Assistant use the
    # device name directly instead of appending a redundant "Collections".
    _attr_name = None
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: GedlingBinCoordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        for collection in self.coordinator.data.collections:
            if collection.date >= today:
                return _event(collection, self.coordinator.data.address)
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return collection events that overlap the requested time window."""
        local_tz = start_date.tzinfo or dt_util.DEFAULT_TIME_ZONE
        start_local = start_date.astimezone(local_tz).date()
        end_local = end_date.astimezone(local_tz).date()
        # If the upper bound contains a non-midnight time, that date is in range.
        if end_date.astimezone(local_tz).time() != datetime.min.time():
            end_local += timedelta(days=1)

        return [
            _event(collection, self.coordinator.data.address)
            for collection in self.coordinator.data.collections
            if start_local <= collection.date < end_local
        ]
