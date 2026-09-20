"""Constants for the Gedling Bin Collections integration."""

from datetime import timedelta

DOMAIN = "gedling_bin_collections"
CONF_CALENDAR_URL = "calendar_url"

OFFICIAL_HOST = "waste.digital.gedling.gov.uk"
OFFICIAL_SEARCH_URL = "https://waste.digital.gedling.gov.uk/w/webpage/bin-collections"

UPDATE_INTERVAL = timedelta(hours=12)
REQUEST_TIMEOUT_SECONDS = 45
CONNECTION_RETRY_SECONDS = 300

SERVICE_GENERAL = "general"
SERVICE_RECYCLING = "recycling"
SERVICE_GLASS = "glass"
SERVICE_GARDEN = "garden"

SERVICE_ORDER = (
    SERVICE_GENERAL,
    SERVICE_RECYCLING,
    SERVICE_GLASS,
    SERVICE_GARDEN,
)

SERVICE_NAMES = {
    SERVICE_GENERAL: "General waste",
    SERVICE_RECYCLING: "Recycling",
    SERVICE_GLASS: "Glass",
    SERVICE_GARDEN: "Garden waste",
}

SERVICE_ICONS = {
    SERVICE_GENERAL: "mdi:trash-can",
    SERVICE_RECYCLING: "mdi:recycle",
    SERVICE_GLASS: "mdi:glass-fragile",
    SERVICE_GARDEN: "mdi:leaf",
}
