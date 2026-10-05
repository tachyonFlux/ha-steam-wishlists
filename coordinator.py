"""Fetch and cache daily wishlist data from the Steamworks partner API."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_URL,
    CONF_APPID,
    CONF_CHART_DAYS,
    CONF_POLL_HOURS,
    CONF_START_DATE,
    DEFAULT_CHART_DAYS,
    DEFAULT_POLL_HOURS,
    DOMAIN,
    FIELDS,
    MAX_FETCH_PER_RUN,
    REFETCH_DAYS,
)

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


class WishlistCoordinator(DataUpdateCoordinator[dict]):
    """Keep a local cache of per-day wishlist numbers and derive totals from it."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._key: str = entry.data[CONF_API_KEY]
        self.appid = int(entry.data[CONF_APPID])
        self._start = date.fromisoformat(entry.data[CONF_START_DATE])
        self._session = async_get_clientsession(hass)
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{self.appid}")
        self._days: dict[str, dict[str, int]] | None = None
        self._backfilling = False
        super().__init__(
            hass,
            _LOGGER,
            name=f"Steam wishlists {self.appid}",
            update_interval=timedelta(
                hours=entry.options.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS)
            ),
        )

    @property
    def chart_days(self) -> int:
        return self.entry.options.get(CONF_CHART_DAYS, DEFAULT_CHART_DAYS)

    async def _fetch_day(self, day: date) -> dict[str, int]:
        params = {"key": self._key, "appid": str(self.appid), "date": day.isoformat()}
        try:
            async with self._session.get(
                API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    raise ConfigEntryAuthFailed(
                        "Steamworks rejected the API key (check the Financial API Group "
                        "key and any IP whitelist)"
                    )
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error talking to Steamworks: {err}") from err

        summary = (payload.get("response") or {}).get("wishlist_summary") or {}
        # Financial endpoints sometimes return numbers as strings.
        return {k: int(summary.get(f"wishlist_{k}") or 0) for k in FIELDS}

    async def _async_update_data(self) -> dict:
        if self._days is None:
            self._days = await self._store.async_load() or {}

        yesterday = date.today() - timedelta(days=1)
        recent = yesterday - timedelta(days=REFETCH_DAYS)

        wanted: list[date] = []
        day = self._start
        while day <= yesterday:
            if day.isoformat() not in self._days or day > recent:
                wanted.append(day)
            day += timedelta(days=1)

        batch, remaining = wanted[:MAX_FETCH_PER_RUN], len(wanted) - MAX_FETCH_PER_RUN
        for index, day in enumerate(batch):
            self._days[day.isoformat()] = await self._fetch_day(day)
            if index < len(batch) - 1:
                await asyncio.sleep(0.5)  # be gentle during the first backfill

        if batch:
            await self._store.async_save(self._days)

        # While backfilling history, come back quickly instead of waiting hours.
        backfilling = remaining > 0
        if backfilling != self._backfilling:
            self._backfilling = backfilling
            self.update_interval = (
                timedelta(seconds=30)
                if backfilling
                else timedelta(
                    hours=self.entry.options.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS)
                )
            )
        if backfilling:
            _LOGGER.debug("Backfilling wishlist history, %s days left", remaining)

        return self._build()

    def _build(self) -> dict:
        def net(value: dict[str, int]) -> int:
            # Purchases and gifts also remove the game from a wishlist.
            return value["adds"] - value["deletes"] - value["purchases"] - value["gifts"]

        keys = sorted(self._days or {})
        if not keys:
            return {"total": None, "net": None, "net_7d": None, "adds": None, "deletes": None}

        running = 0
        series: list[list] = []
        for key in keys:
            running += net(self._days[key])
            series.append([key, running, net(self._days[key])])

        last = self._days[keys[-1]]
        return {
            "total": running,
            "net": net(last),
            "net_7d": sum(net(self._days[k]) for k in keys[-7:]),
            "adds": last["adds"],
            "deletes": last["deletes"],
            "last_date": keys[-1],
            "series": series[-self.chart_days :],
        }
