# Changelog

- **0.1.6**: Fixed startup/reconnection behaviour. The integration no longer blocks config-entry setup on the Gedling website; it reaches Loaded state first, performs the initial council request in the background, retries every five minutes until the first successful fetch, and then returns to the normal 12-hour schedule. Later transient failures also retry after five minutes. Service-specific sensors are added dynamically after data becomes available.
- **0.1.5**: Fix setup/retry lifecycle by explicitly attaching the Home Assistant config entry to the DataUpdateCoordinator.

- **0.1.4**: Retry transient council-site connection failures every 5 minutes (normal polling remains 12-hourly), and make the calendar the primary device entity so new installs use the cleaner `calendar.gedling_bin_collections` default ID.
- **0.1.3**: Corrected calendar, next-collection and collection-tomorrow icons to valid Material Design Icon identifiers.

- **0.1.2**: Added a Collection tomorrow binary sensor with collection details and an automatic midnight state refresh.
- **0.1.1**: Added built-in brand images for the integration UI and explicit icons for the collections calendar and next collection sensor.

- **0.1.0**: Initial calendar and date sensors, address-specific URL configuration, and 12-hour polling.

Repository import: preserve the supplied v0.1.6 implementation and brand assets; add repository metadata and clarify installation, startup, and upgrade documentation.
