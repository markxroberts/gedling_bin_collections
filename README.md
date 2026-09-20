# Gedling Bin Collections for Home Assistant

A small, modern Home Assistant custom integration for **Gedling Borough Council** bin collection dates.

It reads the address-specific **official Gedling waste.digital calendar page** and exposes:

- `calendar.gedling_bin_collections` calendar entity with all collection dates as all-day events
- **Collection tomorrow** binary sensor, refreshed at local midnight
- **Next collection** date sensor
- **Next general waste** collection date sensor
- **Next recycling** collection date sensor
- **Next glass** collection date sensor
- **Next garden waste** collection date sensor when the official calendar contains garden waste

The calendar combines multiple services on the same date, e.g. `Recycling + Glass`.

## Why setup uses the final calendar URL

Gedling's initial address-search page is a JavaScript/AJAX application with CSRF and generated page tokens. The final collection calendar page, however, is deliberately bookmarkable. Using that address-specific final URL lets Home Assistant talk directly to the council website without Selenium, Chromium, or a third-party API.

The integration gets a fresh CSRF value at every update and then requests the rendered page fragment using the site's normal AJAX mechanism. It does **not** store a council login or password.

## Installation

Requires Home Assistant **2026.6.0 or later**.

### HACS custom repository

Add `https://github.com/markxroberts/gedling_bin_collections` as a custom repository in HACS, selecting **Integration**, then download Gedling Bin Collections and restart Home Assistant.

### Manual

Copy:

```text
custom_components/gedling_bin_collections
```

to:

```text
/config/custom_components/gedling_bin_collections
```

Restart Home Assistant.

Then go to **Settings → Devices & services → Add integration** and search for **Gedling Bin Collections**.

## Getting the URL for setup

1. Open the official Gedling bin collection page:
   `https://waste.digital.gedling.gov.uk/w/webpage/bin-collections`
2. Search for and select your address.
3. Choose **View collection days**.
4. Open the **full/yearly collection days** view.
5. Copy the complete URL from the browser address bar.
6. Paste that URL into the integration setup form.

The URL should be on `waste.digital.gedling.gov.uk`, normally under `/w/webpage/...`, and contain a `webpage_token=` query parameter.

Do **not** paste the initial `/w/webpage/bin-collections` search URL.

## Updating

The council website is polled every 12 hours after a successful fetch. Existing configured entries load without waiting for the council website: the initial request runs in the background, with five-minute retries until successful. Later connection failures also retry after five minutes; entities become unavailable until recovery. Initial configuration and reconfiguration still validate the URL against the live council website. Home Assistant's manual integration reload can be used to force an immediate refresh.

If Gedling invalidates the bookmark URL, use **Settings → Devices & services → Gedling Bin Collections → Reconfigure** and paste a newly generated yearly calendar URL.

Existing entity IDs are preserved on upgrade. If your calendar still has the old repeated `collections` suffix, you can rename its entity ID in Home Assistant.

## Entities and automation

The date sensors use Home Assistant's `date` sensor device class. The **Next collection** sensor has attributes including:

- `days_until`
- `collections`
- `raw_collections`
- `address`
- `source_url`

This makes reminders easy without parsing calendar text.

The **Collection tomorrow** binary sensor includes `collection_date`, `collections`, `raw_collections`, `address`, and `source_url` when a collection is due. Its state updates at local midnight without another council request.

Integration brand images are included in `brand/`; entity icons use `icons.json` and explicit Python icons. Restart Home Assistant after updating; refresh the browser if cached brand images remain.

## Notes

- Read-only: the integration cannot change council data.
- Unknown/new collection service names are retained instead of discarded.
- This is an unofficial Home Assistant custom integration and is not maintained or endorsed by Gedling Borough Council.


## Changelog

- **0.1.6**: Fixed startup/reconnection behaviour. The integration no longer blocks config-entry setup on the Gedling website; it reaches Loaded state first, performs the initial council request in the background, retries every five minutes until the first successful fetch, and then returns to the normal 12-hour schedule. Later transient failures also retry after five minutes. Service-specific sensors are added dynamically after data becomes available.
- **0.1.5**: Fix setup/retry lifecycle by explicitly attaching the Home Assistant config entry to the DataUpdateCoordinator.

- **0.1.4**: Retry transient council-site connection failures every 5 minutes (normal polling remains 12-hourly), and make the calendar the primary device entity so new installs use the cleaner `calendar.gedling_bin_collections` default ID.
- **0.1.3**: Corrected calendar, next-collection and collection-tomorrow icons to valid Material Design Icon identifiers.

- **0.1.2**: Added a Collection tomorrow binary sensor with collection details and an automatic midnight state refresh.
- **0.1.1**: Added built-in brand images for the integration UI and explicit icons for the collections calendar and next collection sensor.
