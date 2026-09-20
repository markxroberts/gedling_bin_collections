"""Config flow for Gedling Bin Collections."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    GedlingBinAuthError,
    GedlingBinClient,
    GedlingBinConnectionError,
    GedlingBinParseError,
    validate_calendar_url,
)
from .const import CONF_CALENDAR_URL, DOMAIN


async def _validate(hass, calendar_url: str):
    """Validate a calendar URL and return live data."""
    normalized = validate_calendar_url(calendar_url)
    client = GedlingBinClient(async_get_clientsession(hass), normalized)
    return normalized, await client.async_fetch()


class GedlingBinConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Gedling Bin Collections configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                calendar_url, data = await _validate(
                    self.hass, user_input[CONF_CALENDAR_URL]
                )
            except ValueError:
                errors[CONF_CALENDAR_URL] = "invalid_url"
            except GedlingBinAuthError:
                errors[CONF_CALENDAR_URL] = "invalid_or_expired"
            except GedlingBinParseError:
                errors[CONF_CALENDAR_URL] = "no_calendar_data"
            except GedlingBinConnectionError:
                errors["base"] = "cannot_connect"
            else:
                identity = data.address or calendar_url
                unique_id = sha256(identity.casefold().encode()).hexdigest()[:24]
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data.address or "Gedling bin collections",
                    data={CONF_CALENDAR_URL: calendar_url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_CALENDAR_URL): str}
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                calendar_url, data = await _validate(
                    self.hass, user_input[CONF_CALENDAR_URL]
                )
            except ValueError:
                errors[CONF_CALENDAR_URL] = "invalid_url"
            except GedlingBinAuthError:
                errors[CONF_CALENDAR_URL] = "invalid_or_expired"
            except GedlingBinParseError:
                errors[CONF_CALENDAR_URL] = "no_calendar_data"
            except GedlingBinConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_CALENDAR_URL: calendar_url},
                    title=data.address or entry.title,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CALENDAR_URL,
                        default=entry.data[CONF_CALENDAR_URL],
                    ): str
                }
            ),
            errors=errors,
        )
