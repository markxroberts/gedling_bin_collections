"""Data update coordinator for Gedling Bin Collections."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import GedlingBinClient, GedlingBinConnectionError, GedlingBinError
from .const import CONNECTION_RETRY_SECONDS, DOMAIN, UPDATE_INTERVAL
from .models import GedlingBinData

_LOGGER = logging.getLogger(__name__)


class GedlingBinCoordinator(DataUpdateCoordinator[GedlingBinData]):
    """Coordinate retrieval of the Gedling collection calendar."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: GedlingBinClient,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=CONNECTION_RETRY_SECONDS),
        )
        self.client = client
        self._has_successful_update = False
        # DataUpdateCoordinator.data is None until its first successful update by
        # default.  We intentionally allow this integration to load while the
        # council site is offline, so provide a safe empty initial value for the
        # calendar/sensor platforms to read.  A failed refresh will still set
        # last_update_success=False, making CoordinatorEntity instances
        # unavailable as normal.
        self.data = GedlingBinData(
            address=None,
            source_url=client.calendar_url,
            collections=(),
        )

    async def _async_update_data(self) -> GedlingBinData:
        try:
            data = await self.client.async_fetch()
        except GedlingBinConnectionError as err:
            # The normal schedule is deliberately infrequent because collection
            # dates change rarely.  A transient outage should not therefore leave
            # the integration unavailable for the full normal update interval.
            raise UpdateFailed(
                str(err), retry_after=CONNECTION_RETRY_SECONDS
            ) from err
        except GedlingBinError as err:
            raise UpdateFailed(str(err)) from err

        # Until the first successful fetch we deliberately poll every five
        # minutes.  This means an installation/restart during a council outage
        # cannot get stranded.  After recovery, return to the normal 12-hour
        # schedule; later transient failures still use retry_after above.
        if not self._has_successful_update:
            self._has_successful_update = True
            self.update_interval = UPDATE_INTERVAL

        return data
