"""HTTP client for the Gedling Borough Council bin collection website."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import date
from html.parser import HTMLParser
import json
import re
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

from .const import (
    OFFICIAL_HOST,
    REQUEST_TIMEOUT_SECONDS,
    SERVICE_GARDEN,
    SERVICE_GENERAL,
    SERVICE_GLASS,
    SERVICE_ORDER,
    SERVICE_RECYCLING,
)
from .models import BinCollection, GedlingBinData


class GedlingBinError(Exception):
    """Base exception for Gedling bin data errors."""


class GedlingBinConnectionError(GedlingBinError):
    """Raised when the council website cannot be reached."""


class GedlingBinAuthError(GedlingBinError):
    """Raised when a bookmarked calendar URL is no longer valid."""


class GedlingBinParseError(GedlingBinError):
    """Raised when collection data cannot be parsed."""


class _DataParamsParser(HTMLParser):
    """Collect data-params attributes from rendered page fragments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data_params: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        for key, value in attrs:
            if key == "data-params" and value:
                self.data_params.append(value)


def validate_calendar_url(url: str) -> str:
    """Validate and normalize an official Gedling calendar URL."""
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != OFFICIAL_HOST:
        raise ValueError("The URL must be an HTTPS Gedling waste.digital URL")
    if not parsed.path.startswith("/w/webpage/"):
        raise ValueError("The URL is not a Gedling webpage URL")
    if parsed.path.endswith("/bin-collections"):
        raise ValueError(
            "Use the final yearly collection calendar URL, not the search page"
        )
    if "webpage_token=" not in parsed.query:
        raise ValueError("The URL does not contain a webpage_token")
    return url


def _extract_csrf(html: str) -> str:
    """Extract the Netcall/Liberty CSRF token from initial page HTML."""
    patterns = (
        r"\bvar\s+CSRF\s*=\s*['\"]([^'\"]+)['\"]",
        r"\bCSRF\s*=\s*['\"]([^'\"]+)['\"]",
        r'name=["\']form_check_ajax["\'][^>]*value=["\']([^"\']+)',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    raise GedlingBinAuthError(
        "Could not obtain the council website CSRF token; the saved calendar URL "
        "may have expired or the website may have changed"
    )


def _find_values(value: Any, key: str) -> Iterable[Any]:
    """Yield values for a key at any level of a JSON-compatible object."""
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if child_key == key:
                yield child_value
            yield from _find_values(child_value, key)
    elif isinstance(value, list):
        for child in value:
            yield from _find_values(child, key)


def _decode_data_params(html: str) -> list[Any]:
    parser = _DataParamsParser()
    parser.feed(html)
    decoded: list[Any] = []
    for raw in parser.data_params:
        try:
            decoded.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return decoded


def _looks_like_collection_months(value: Any) -> bool:
    """Return True when a value resembles Gedling's yearly collection structure."""
    if not isinstance(value, list) or not value:
        return False
    return any(
        isinstance(item, dict)
        and isinstance(item.get("dates"), list)
        and ("month" in item or item.get("dates"))
        for item in value
    )


def _extract_collection_months(objects: Iterable[Any]) -> list[dict[str, Any]]:
    """Find the yearly collections list inside widget data."""
    for obj in objects:
        for candidate in _find_values(obj, "collections"):
            if _looks_like_collection_months(candidate):
                return candidate
    raise GedlingBinParseError(
        "No yearly bin collection data was found in the Gedling calendar page. "
        "Open the council website, select your address, choose the full/yearly "
        "collection view, then copy that final URL into the integration."
    )


def _extract_address(objects: Iterable[Any]) -> str | None:
    """Extract the matched property address from widget data, if present."""
    for obj in objects:
        for candidate in _find_values(obj, "address"):
            if isinstance(candidate, str) and candidate.strip():
                return " ".join(candidate.split())
    return None


def _normalize_service(raw: str) -> str:
    text = " ".join(raw.lower().replace("&", " and ").split())
    if "garden" in text:
        return SERVICE_GARDEN
    if "glass" in text:
        return SERVICE_GLASS
    if "recycl" in text:
        return SERVICE_RECYCLING
    if "general" in text or "refuse" in text or "residual" in text:
        return SERVICE_GENERAL

    # Preserve future/unknown service names rather than silently dropping them.
    cleaned = re.sub(r"\s+collection\s+service\s*$", "", text).strip()
    return cleaned.replace(" ", "_") or "unknown"


def _parse_collections(months: list[dict[str, Any]]) -> tuple[BinCollection, ...]:
    result: dict[date, tuple[set[str], set[str]]] = {}

    for month in months:
        dates = month.get("dates")
        if not isinstance(dates, list):
            continue
        for item in dates:
            if not isinstance(item, dict):
                continue
            raw_date = item.get("date")
            raw_services = item.get("collections")
            if not isinstance(raw_date, str) or not isinstance(raw_services, list):
                continue
            try:
                collection_date = date.fromisoformat(raw_date)
            except ValueError:
                continue

            normalized_set, raw_set = result.setdefault(
                collection_date, (set(), set())
            )
            for raw_service in raw_services:
                if not isinstance(raw_service, str) or not raw_service.strip():
                    continue
                raw_set.add(" ".join(raw_service.split()))
                normalized_set.add(_normalize_service(raw_service))

    if not result:
        raise GedlingBinParseError("The calendar page contained no valid collection dates")

    known_order = {name: index for index, name in enumerate(SERVICE_ORDER)}

    def service_sort(service: str) -> tuple[int, str]:
        return (known_order.get(service, len(known_order)), service)

    return tuple(
        BinCollection(
            date=collection_date,
            services=tuple(sorted(services, key=service_sort)),
            raw_services=tuple(sorted(raw_services)),
        )
        for collection_date, (services, raw_services) in sorted(result.items())
    )


def parse_page_fragment(html: str, source_url: str) -> GedlingBinData:
    """Parse collection data from rendered council page HTML."""
    objects = _decode_data_params(html)
    months = _extract_collection_months(objects)
    return GedlingBinData(
        address=_extract_address(objects),
        source_url=source_url,
        collections=_parse_collections(months),
    )


class GedlingBinClient:
    """Client that retrieves an address-specific collection calendar."""

    def __init__(self, session: ClientSession, calendar_url: str) -> None:
        self._session = session
        self.calendar_url = validate_calendar_url(calendar_url)
        self._timeout = ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

    async def _read_text(self, response: ClientResponse) -> str:
        try:
            return await response.text()
        except UnicodeError as err:
            raise GedlingBinParseError("The council returned unreadable data") from err

    async def async_fetch(self) -> GedlingBinData:
        """Fetch and parse the latest collection schedule."""
        try:
            async with self._session.get(
                self.calendar_url,
                timeout=self._timeout,
                headers={"Accept": "text/html,application/xhtml+xml"},
            ) as response:
                if response.status in (401, 403, 404):
                    raise GedlingBinAuthError(
                        f"The saved Gedling calendar URL returned HTTP {response.status}"
                    )
                response.raise_for_status()
                initial_html = await self._read_text(response)

            csrf = _extract_csrf(initial_html)
            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": f"https://{OFFICIAL_HOST}",
                "Referer": self.calendar_url,
                "X-Requested-With": "XMLHttpRequest",
            }
            form_data = {
                "_dummy": "1",
                "_session_storage": '{"_global":{}}',
                "_update_page_content_request": "1",
                "form_check_ajax": csrf,
            }

            async with self._session.post(
                self.calendar_url,
                timeout=self._timeout,
                headers=headers,
                data=form_data,
            ) as response:
                if response.status in (401, 403, 404):
                    raise GedlingBinAuthError(
                        f"The saved Gedling calendar URL returned HTTP {response.status}"
                    )
                response.raise_for_status()
                text = await self._read_text(response)
                content_type = response.headers.get("Content-Type", "")

            fragment = text
            if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as err:
                    raise GedlingBinParseError(
                        "The council returned invalid JSON"
                    ) from err
                if isinstance(payload, dict) and isinstance(payload.get("data"), str):
                    fragment = payload["data"]
                else:
                    # Some platform versions may return the widget JSON directly.
                    objects = [payload]
                    months = _extract_collection_months(objects)
                    return GedlingBinData(
                        address=_extract_address(objects),
                        source_url=self.calendar_url,
                        collections=_parse_collections(months),
                    )

            return parse_page_fragment(fragment, self.calendar_url)

        except GedlingBinError:
            raise
        except (ClientError, asyncio.TimeoutError) as err:
            raise GedlingBinConnectionError(
                "Unable to contact the Gedling bin collection website"
            ) from err
