"""Constants for the Steam Wishlists integration."""

DOMAIN = "steam_wishlist"

CONF_APPID = "appid"
CONF_START_DATE = "start_date"
CONF_POLL_HOURS = "poll_hours"
CONF_CHART_DAYS = "chart_days"

DEFAULT_NAME = "Steam wishlists"
DEFAULT_POLL_HOURS = 3
DEFAULT_CHART_DAYS = 90

# Valve may revise recent days, so re-pull this many each run.
REFETCH_DAYS = 3
# Cap per refresh so the first backfill never blocks setup for long.
MAX_FETCH_PER_RUN = 45

API_URL = "https://partner.steam-api.com/IPartnerFinancialsService/GetAppWishlistReporting/v1/"
FIELDS = ("adds", "deletes", "purchases", "gifts")
